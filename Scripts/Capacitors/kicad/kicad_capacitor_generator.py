#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import tempfile
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "LCSC"))
from lcsc import apply_kicad, ensure_database


BASE_SYMBOL_TEMPLATE = """\
\t(symbol \"{base_symbol}\"
\t\t(pin_numbers
\t\t\t(hide yes)
\t\t)
\t\t(pin_names
\t\t\t(hide yes)
\t\t)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(in_pos_files yes)
\t\t(duplicate_pin_numbers_are_jumpers no)
{properties}
\t\t(symbol \"{base_symbol}_1_0\"
\t\t\t(polyline
\t\t\t\t(pts
\t\t\t\t\t(xy -2.54 0) (xy -0.381 0)
\t\t\t\t)
\t\t\t\t(stroke
\t\t\t\t\t(width 0)
\t\t\t\t\t(type solid)
\t\t\t\t)
\t\t\t\t(fill
\t\t\t\t\t(type none)
\t\t\t\t)
\t\t\t)
\t\t\t(polyline
\t\t\t\t(pts
\t\t\t\t\t(xy 0.381 0) (xy 2.54 0)
\t\t\t\t)
\t\t\t\t(stroke
\t\t\t\t\t(width 0)
\t\t\t\t\t(type solid)
\t\t\t\t)
\t\t\t\t(fill
\t\t\t\t\t(type none)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(symbol \"{base_symbol}_1_1\"
\t\t\t(rectangle
\t\t\t\t(start -0.8636 2.032)
\t\t\t\t(end -0.3556 -2.032)
\t\t\t\t(stroke
\t\t\t\t\t(width 0)
\t\t\t\t\t(type solid)
\t\t\t\t)
\t\t\t\t(fill
\t\t\t\t\t(type outline)
\t\t\t\t)
\t\t\t)
\t\t\t(rectangle
\t\t\t\t(start 0.3556 2.032)
\t\t\t\t(end 0.8636 -2.032)
\t\t\t\t(stroke
\t\t\t\t\t(width 0)
\t\t\t\t\t(type solid)
\t\t\t\t)
\t\t\t\t(fill
\t\t\t\t\t(type outline)
\t\t\t\t)
\t\t\t)
\t\t\t(pin passive line
\t\t\t\t(at -2.54 0 0)
\t\t\t\t(length 0)
\t\t\t\t(name \"C1\"
\t\t\t\t\t(effects
\t\t\t\t\t\t(font
\t\t\t\t\t\t\t(size 1.016 1.016)
\t\t\t\t\t\t)
\t\t\t\t\t)
\t\t\t\t)
\t\t\t\t(number \"1\"
\t\t\t\t\t(effects
\t\t\t\t\t\t(font
\t\t\t\t\t\t\t(size 1.016 1.016)
\t\t\t\t\t\t)
\t\t\t\t\t)
\t\t\t\t)
\t\t\t)
\t\t\t(pin passive line
\t\t\t\t(at 2.54 0 180)
\t\t\t\t(length 0)
\t\t\t\t(name \"C2\"
\t\t\t\t\t(effects
\t\t\t\t\t\t(font
\t\t\t\t\t\t\t(size 1.016 1.016)
\t\t\t\t\t\t)
\t\t\t\t\t)
\t\t\t\t)
\t\t\t\t(number \"2\"
\t\t\t\t\t(effects
\t\t\t\t\t\t(font
\t\t\t\t\t\t\t(size 1.016 1.016)
\t\t\t\t\t\t)
\t\t\t\t\t)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(embedded_fonts no)
\t)
"""


@dataclass(frozen=True)
class SeriesConfig:
    name: str
    package: str
    footprint: str
    ki_fp_filters: str
    datasheet: str
    manufacturer: str
    base_symbol: str
    description_template: str


@dataclass(frozen=True)
class PartRow:
    value: str
    cap_code: str
    mpn: str
    dielectric: str
    tolerance: str
    voltage: str
    verification: str
    lcsc: str = ""
    datasheet: str = ""


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalize_value_token(value: str) -> str:
    text = value.strip().lower().replace(" ", "")
    text = text.replace("ÃƒÅ½Ã‚Â¼", "u").replace("Ãƒâ€šÃ‚Âµ", "u")
    text = text.replace("farad", "f").replace("farads", "f")
    if text.endswith("f") and len(text) > 1:
        text = text[:-1]

    decimal_match = re.fullmatch(r"(\d+)\.(\d+)([pnum])", text)
    if decimal_match:
        return f"{decimal_match.group(1)}{decimal_match.group(3)}{decimal_match.group(2)}"

    plain_match = re.fullmatch(r"(\d+)([pnum])", text)
    if plain_match:
        return text

    embedded_match = re.fullmatch(r"(\d+)([pnum])(\d+)", text)
    if embedded_match:
        return text

    raise ValueError(f"unsupported capacitor value token: {value}")


def parse_tolerance_percent(text: str) -> int:
    match = re.search(r"(\d+)", text)
    if not match:
        return 999
    return int(match.group(1))


def parse_voltage_volts(text: str) -> float:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
    if not match:
        return 0.0
    return float(match.group(1))


def dielectric_score(dielectric: str) -> int:
    key = dielectric.upper()
    if key in {"C0G", "NP0"}:
        return 5
    if key == "X7R":
        return 4
    if key == "X5R":
        return 3
    if key == "X7S":
        return 2
    if key == "Y5V":
        return 0
    return 1


def capacitance_pf(value: str) -> Decimal:
    token = normalize_value_token(value)
    match = re.fullmatch(r"(\d+)([pnum])(\d*)", token)
    return Decimal(match[1] + "." + (match[3] or "0")) * {
        "p": 1, "n": 1000, "u": 1000000, "m": 1000000000,
    }[match[2]]


def capacitor_catalogue(path: Path) -> list[dict]:
    """Cache CC records once per source snapshot; the large source has no MPN index."""
    path = path.resolve()
    stat = path.stat()
    signature = {"version": 1, "source": str(path), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    cache_path = path.with_name(path.name + ".capacitors.json")
    try:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if cached["signature"] == signature and isinstance(cached["records"], list):
            return cached["records"]
    except (OSError, ValueError, KeyError, TypeError):
        pass

    print("Building capacitor lookup cache from local LCSC database...", flush=True)
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        records = [dict(row) for row in connection.execute(
            "SELECT lcsc,mfr,package,manufacturer,attributes,datasheet FROM jlc_components "
            "WHERE present=1 AND mfr LIKE 'CC%'"
        )]
    finally:
        connection.close()
    # Do not cache a scan if the source was replaced or updated during it.
    after = path.stat()
    if (after.st_size, after.st_mtime_ns) != (stat.st_size, stat.st_mtime_ns):
        raise ValueError("LCSC database changed during lookup; rerun generation")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            json.dump({"signature": signature, "records": records}, output)
        temporary.replace(cache_path)
    except OSError as error:
        print(f"Could not save capacitor lookup cache: {error}", flush=True)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return records


def database_parts(path: Path, series: SeriesConfig, requested: set[str]) -> list[PartRow]:
    """Validate catalogue MPNs against their electrical attributes, offline."""
    wanted = {capacitance_pf(value): value for value in requested}
    valid: dict[str, list[PartRow]] = {}
    voltages = {"5": "6.3V", "6": "10V", "7": "16V", "8": "25V", "9": "50V", "0": "100V"}
    tolerances = {"J": "5%", "K": "10%", "M": "20%"}
    for record in capacitor_catalogue(path):
        mpn = record["mfr"].strip().upper()
        match = re.fullmatch(re.escape(series.name) + r"([JKM])[RK](NPO|X7R|X5R)([567890])B([NB])(\d{3}|\dR\d)", mpn)
        if not match or record["package"] != series.package or record["manufacturer"].strip().upper() != "YAGEO":
            continue
        tolerance, dielectric, voltage, process, code = match.groups()
        if process != ("N" if dielectric == "NPO" else "B"):
            continue
        pf = Decimal(code.replace("R", ".")) if "R" in code else Decimal(code[:2]) * 10 ** int(code[2])
        if pf not in wanted:
            continue
        try:
            attrs = json.loads(record["attributes"])
            if not isinstance(attrs, dict):
                continue
            if capacitance_pf(attrs["Capacitance"]) != pf:
                continue
            if attrs["Temperature Coefficient"].upper() not in ({"NPO", "NP0", "C0G"} if dielectric == "NPO" else {dielectric}):
                continue
            if parse_tolerance_percent(attrs["Tolerance"]) != int(tolerances[tolerance][:-1]):
                continue
            if parse_voltage_volts(attrs["Voltage Rating"]) != parse_voltage_volts(voltages[voltage]):
                continue
        except (KeyError, TypeError, ValueError):
            continue
        valid.setdefault(mpn, []).append(PartRow(
            wanted[pf], code, mpn, "C0G" if dielectric == "NPO" else dielectric,
            tolerances[tolerance], voltages[voltage], "lcsc_database",
            "C" + str(record["lcsc"]), record["datasheet"],
        ))
    # Multiple fully specified catalogue codes for one MPN require review.
    return [rows[0] for rows in valid.values() if len(rows) == 1]


def select_database_parts(rows: list[PartRow]) -> dict[str, PartRow]:
    selected = {}
    for row in sorted(rows, key=lambda r: r.mpn):
        key = normalize_value_token(row.value)
        def rank(part):
            return (
                part.dielectric == "X7R" if capacitance_pf(part.value) < 1000000 else True,
                -abs(parse_tolerance_percent(part.tolerance) - 10),
                parse_voltage_volts(part.voltage), dielectric_score(part.dielectric),
            )
        if key not in selected or rank(row) > rank(selected[key]):
            selected[key] = row
    return selected


def property_block(name: str, value: str, y: float, show_name: str = "yes", hidden: bool = True, do_not_autoplace: str = "no") -> str:
    hide = "\n\t\t\t(hide yes)" if hidden else ""
    return (
        f"\t\t(property \"{name}\" \"{value}\"\n"
        f"\t\t\t(at 0 {y} 0)\n"
        f"\t\t\t(show_name {show_name})\n"
        f"\t\t\t(do_not_autoplace {do_not_autoplace})"
        f"{hide}\n"
        f"\t\t\t(effects\n"
        f"\t\t\t\t(font\n"
        f"\t\t\t\t\t(size 1.27 1.27)\n"
        f"\t\t\t\t)\n"
        f"\t\t\t)\n"
        f"\t\t)"
    )


def load_series_config(config: dict, series_name: str) -> SeriesConfig:
    defaults = config["defaults"]
    series_data = config["series"][series_name]
    return SeriesConfig(
        name=series_name,
        package=series_data["package"],
        footprint=series_data.get("footprint", defaults["footprint"]),
        ki_fp_filters=series_data.get("ki_fp_filters", defaults["ki_fp_filters"]),
        datasheet=series_data.get("datasheet", defaults["datasheet"]),
        manufacturer=series_data.get("manufacturer", defaults["manufacturer"]),
        base_symbol=series_data.get("base_symbol", defaults["base_symbol"]),
        description_template=series_data.get("description_template", defaults["description_template"]),
    )


def range_values(preset: dict) -> set[str]:
    bases = {
        "E12": (10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82),
        "E24": (10, 11, 12, 13, 15, 16, 18, 20, 22, 24, 27, 30,
                33, 36, 39, 43, 47, 51, 56, 62, 68, 75, 82, 91),
    }
    minimum, maximum = capacitance_pf(preset["min_value"]), capacitance_pf(preset["max_value"])
    if minimum <= 0 or maximum < minimum:
        raise ValueError("Capacitance range must have 0 < min_value <= max_value")
    if preset["series"] not in bases:
        raise ValueError("Capacitance range series must be E12 or E24")
    values = set()
    for exponent in range(minimum.adjusted(), maximum.adjusted() + 1):
        for base in bases[preset["series"]]:
            pf = Decimal(base) * Decimal(10) ** (exponent - 1)
            if minimum <= pf <= maximum:
                unit, scale = ("u", 1000000) if pf >= 1000000 else ("n", 1000) if pf >= 1000 else ("p", 1)
                number = format(pf / scale, "f")
                if "." in number:
                    number = number.rstrip("0").rstrip(".")
                values.add(normalize_value_token(number + unit))
    return values


def resolve_requested_values(args_values: list[str], values_file: Path | None, config: dict, preset: str) -> set[str]:
    raw_tokens: list[str] = []

    if args_values or values_file is not None:
        for value_arg in args_values:
            raw_tokens.extend(part for part in re.split(r"[;,\s]+", value_arg) if part)
        if values_file is not None:
            raw_tokens.extend(read_lines(values_file))
    else:
        definition = config["presets"][preset]
        if isinstance(definition, dict):
            return range_values(definition)
        raw_tokens.extend(definition)

    return {normalize_value_token(token) for token in raw_tokens}


def render_symbol(series: SeriesConfig, row: PartRow) -> tuple[str, list[str]]:
    resolved_mpn = row.mpn.strip()
    if not resolved_mpn or row.verification != "lcsc_database" or not row.lcsc:
        raise ValueError("Only database-validated parts can be rendered")
    status = "VERIFIED"
    description = series.description_template.format(
        value=row.value,
        dielectric=row.dielectric,
        tolerance=row.tolerance,
        voltage=row.voltage,
    )

    properties = "\n".join(
        [
            property_block("Reference", "C", 1.905, show_name="no", hidden=False, do_not_autoplace="yes"),
            property_block("Value", row.value, -1.905, show_name="no", hidden=False, do_not_autoplace="yes"),
            property_block("Footprint", series.footprint, -6.985),
            property_block("Datasheet", row.datasheet or series.datasheet, -9.525),
            property_block("Description", description, 0),
            property_block("Manufacturer", series.manufacturer, -13.335),
            property_block("MFN", series.manufacturer, -14.2875),
            property_block("MPN", resolved_mpn, -15.24),
            property_block("Dielectric", row.dielectric, -17.145),
            property_block("Tolerance", row.tolerance, -19.05),
            property_block("Voltage Rating", row.voltage, -20.955),
            property_block("Package", series.package, -22.86),
            property_block("Series", series.name, -24.765),
            property_block("Cap Code", row.cap_code, -26.67),
            property_block("Verification", row.verification, -28.575),
            property_block("Verification Status", status, -30.48),
        ]
    )

    block = (
        f"\t(symbol \"{resolved_mpn}\"\n"
        f"\t\t(extends \"{series.base_symbol}\")\n"
        f"{properties}\n"
        f"\t\t(embedded_fonts no)\n"
        f"\t)"
    )

    csv_row = [
        series.name,
        series.package,
        row.value,
        row.cap_code,
        resolved_mpn,
        row.dielectric,
        row.tolerance,
        row.voltage,
        row.verification,
        status,
    ]
    return block, csv_row


def render_no_mount_symbol(series: SeriesConfig) -> str:
    properties = "\n".join(
        [
            property_block("Reference", "C", 1.905, show_name="no", hidden=False, do_not_autoplace="yes"),
            property_block("Value", "N.M.", -1.905, show_name="no", hidden=False, do_not_autoplace="yes"),
            property_block("Footprint", series.footprint, -6.985),
            property_block("Datasheet", series.datasheet, -9.525),
            property_block("Description", "No mount capacitor", 0),
            property_block("Manufacturer", series.manufacturer, -13.335),
            property_block("MFN", series.manufacturer, -14.2875),
            property_block("MPN", "N.M.", -15.24),
            property_block("Package", series.package, -22.86),
            property_block("Series", series.name, -24.765),
        ]
    )

    return (
        f"\t(symbol \"{series.name}_N.M.\"\n"
        f"\t\t(extends \"{series.base_symbol}\")\n"
        f"{properties}\n"
        f"\t\t(embedded_fonts no)\n"
        f"\t)"
    )


def build_library(series: SeriesConfig, symbol_blocks: list[str]) -> str:
    header = "\n".join(
        [
            "(kicad_symbol_lib",
            "\t(version 20251024)",
            '\t(generator "kicad_symbol_editor")',
            '\t(generator_version "10.0")',
        ]
    )

    base_properties = "\n".join(
        [
            property_block("Reference", "C", 1.905, show_name="no", hidden=False, do_not_autoplace="yes"),
            property_block("Value", "XXXX", -1.905, show_name="no", hidden=False, do_not_autoplace="yes"),
            property_block("Footprint", series.footprint, -6.985),
            property_block("Datasheet", series.datasheet, -9.525),
            property_block("Description", "MLCC placeholder", 0),
            property_block("Manufacturer", series.manufacturer, -13.335),
            property_block("MFN", series.manufacturer, -14.2875),
            property_block("Package", series.package, -15.24),
            property_block("Series", series.name, -17.145),
            property_block("ki_fp_filters", series.ki_fp_filters, -19.05),
        ]
    )

    base_symbol = BASE_SYMBOL_TEMPLATE.format(base_symbol=series.base_symbol, properties=base_properties)
    no_mount_symbol = render_no_mount_symbol(series)
    return "\n".join([header, base_symbol, no_mount_symbol, *symbol_blocks, ")\n"])


def resolve_path(path_text: str | None, default_path: Path) -> Path:
    if not path_text:
        return default_path
    return Path(path_text)


def resolve_series_names(series_args: list[str], config: dict) -> list[str]:
    if not series_args:
        return sorted(config["series"].keys())

    selected: list[str] = []
    seen: set[str] = set()
    for raw in series_args:
        for token in re.split(r"[;,\s]+", raw):
            if not token:
                continue
            if token not in config["series"]:
                raise ValueError(f"unknown series: {token}")
            if token in seen:
                continue
            seen.add(token)
            selected.append(token)
    return selected


def main() -> int:
    script_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(description="Generate KiCad capacitor symbol libraries from curated Yageo MLCC rows.")
    parser.add_argument("--config", default=str(script_dir / "kicad_capacitor_config.json"), help="Path to capacitor JSON config.")
    parser.add_argument(
        "--series",
        action="append",
        default=[],
        help="Series name(s) from config. Repeatable or comma-separated. If omitted, all supported series are generated.",
    )
    parser.add_argument("--preset", default=None, help="Value preset from config presets.")
    parser.add_argument("--values", action="append", default=[], help="Custom value list. Comma, semicolon, or whitespace separated.")
    parser.add_argument("--values-file", default=None, help="Text file with one value per line.")
    parser.add_argument("--output", default=None, help="Output .kicad_sym path.")
    parser.add_argument("--csv-output", default=None, help="Companion CSV manifest output path.")
    parser.add_argument("--no-csv-output", action="store_true", help="Do not write the companion CSV manifest.")
    parser.add_argument("--database", type=Path, default=None, help="Local jlcparts SQLite database for automatic MPN/spec validation.")
    args = parser.parse_args()

    config = load_json(Path(args.config))
    database = args.database or Path(__file__).resolve().parents[3] / config["generator"].get(
        "database", "Data/LCSC/jlcparts/cache.sqlite3"
    )
    ensure_database(database)
    preset = args.preset or config["generator"]["default_preset"]
    if preset not in config["presets"]:
        raise ValueError(f"unknown preset: {preset}")

    series_names = resolve_series_names(args.series, config)

    if len(series_names) > 1 and (args.output or args.csv_output):
        raise ValueError("--output and --csv-output are only allowed when generating a single series")

    values_file = Path(args.values_file) if args.values_file else None

    csv_header = [
        "series",
        "package",
        "value",
        "cap_code",
        "selected_mpn",
        "dielectric",
        "tolerance",
        "voltage",
        "verification",
        "status",
    ]

    for series_name in series_names:
        requested_values = resolve_requested_values(args.values, values_file, config, preset)

        series = load_series_config(config, series_name)
        selected_by_value = select_database_parts(database_parts(database, series, requested_values))
        print(f"{series_name}: {len(selected_by_value)}/{len(requested_values)} values validated against {database}")

        symbol_blocks: list[str] = []
        csv_rows: list[list[str]] = []

        for value_key in sorted(requested_values):
            row = selected_by_value.get(value_key)
            if row is None:
                continue

            symbol_block, csv_row = render_symbol(series, row)
            symbol_blocks.append(symbol_block)
            csv_rows.append(csv_row)

        if len(series_names) == 1:
            output_path = resolve_path(args.output, script_dir / f"{series.name}.generated.kicad_sym")
            csv_output_path = resolve_path(args.csv_output, output_path.with_suffix(".manifest.csv"))
        else:
            output_path = script_dir / f"{series.name}.generated.kicad_sym"
            csv_output_path = output_path.with_suffix(".manifest.csv")

        cache = {}
        for row in selected_by_value.values():
            cache[row.mpn] = {"mpn": row.mpn, "lcsc": row.lcsc}
        output_path.write_text(apply_kicad(build_library(series, symbol_blocks), cache), encoding="utf-8", newline="\n")

        if not args.no_csv_output:
            lines = [",".join(csv_header)] + [",".join(row) for row in csv_rows]
            csv_output_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

        print(f"Wrote {output_path}")
        if not args.no_csv_output:
            print(f"Wrote {csv_output_path}")
        print(
            "Generated "
            f"{len(symbol_blocks)} symbols for {series.name} "
            f"using {'custom list' if args.values or args.values_file else preset}"
        )

        missing = sorted(value for value in requested_values if value not in selected_by_value)
        if missing:
            print("No unambiguous database match with matching specs:", ", ".join(missing))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
