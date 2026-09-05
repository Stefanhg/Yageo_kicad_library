#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "LCSC"))
from lcsc import apply_kicad, load_cache


E12_BASE = (
    1.0,
    1.2,
    1.5,
    1.8,
    2.2,
    2.7,
    3.3,
    3.9,
    4.7,
    5.6,
    6.8,
    8.2,
)

E24_BASE = (
    1.0,
    1.1,
    1.2,
    1.3,
    1.5,
    1.6,
    1.8,
    2.0,
    2.2,
    2.4,
    2.7,
    3.0,
    3.3,
    3.6,
    3.9,
    4.3,
    4.7,
    5.1,
    5.6,
    6.2,
    6.8,
    7.5,
    8.2,
    9.1,
)


BASE_SYMBOL_TEMPLATE = """\
	(symbol \"{base_symbol}\"
		(pin_numbers
			(hide yes)
		)
		(pin_names
			(hide yes)
		)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(in_pos_files yes)
		(duplicate_pin_numbers_are_jumpers no)
{properties}
		(symbol \"{base_symbol}_1_0\"
			(polyline
				(pts
					(xy -2.54 -0.889) (xy -2.54 0.889)
				)
				(stroke
					(width 0)
					(type solid)
				)
				(fill
					(type none)
				)
			)
			(polyline
				(pts
					(xy -2.54 -0.889) (xy 2.54 -0.889)
				)
				(stroke
					(width 0)
					(type solid)
				)
				(fill
					(type none)
				)
			)
			(polyline
				(pts
					(xy 2.54 0.889) (xy -2.54 0.889)
				)
				(stroke
					(width 0)
					(type solid)
				)
				(fill
					(type none)
				)
			)
			(polyline
				(pts
					(xy 2.54 -0.889) (xy 2.54 0.889)
				)
				(stroke
					(width 0)
					(type solid)
				)
				(fill
					(type none)
				)
			)
		)
		(symbol \"{base_symbol}_1_1\"
			(pin passive line
				(at 5.08 0 180)
				(length 2.54)
				(name \"R1\"
					(effects
						(font
							(size 1.016 1.016)
						)
					)
				)
				(number \"1\"
					(effects
						(font
							(size 1.016 1.016)
						)
					)
				)
			)
			(pin passive line
				(at -5.08 0 0)
				(length 2.54)
				(name \"R2\"
					(effects
						(font
							(size 1.016 1.016)
						)
					)
				)
				(number \"2\"
					(effects
						(font
							(size 1.016 1.016)
						)
					)
				)
			)
		)
		(embedded_fonts no)
	)
"""


PROPERTY_TEMPLATE = """\
		(property \"Reference\" \"R\"
			(at 0 1.905 0)
			(show_name no)
			(do_not_autoplace yes)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property \"Value\" \"{value}\"
			(at 0 -1.905 0)
			(show_name no)
			(do_not_autoplace yes)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property \"Footprint\" \"{footprint}\"
			(at 0 -6.985 0)
			(show_name no)
			(do_not_autoplace no)
			(hide yes)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property \"Datasheet\" \"{datasheet}\"
			(at 0 -9.525 0)
			(show_name no)
			(do_not_autoplace no)
			(hide yes)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property \"Description\" \"{description}\"
			(at 0 0 0)
			(show_name no)
			(do_not_autoplace no)
			(hide yes)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property \"Manufacturer\" \"{manufacturer}\"
			(at 0 -13.335 0)
			(show_name yes)
			(do_not_autoplace no)
			(hide yes)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property \"MPN\" \"{mpn}\"
			(at 0 -15.24 0)
			(show_name yes)
			(do_not_autoplace no)
			(hide yes)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property \"Tolerance\" \"{tolerance}\"
			(at 0 -17.145 0)
			(show_name yes)
			(do_not_autoplace no)
			(hide yes)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property \"Voltage Rating\" \"{voltage_rating}\"
			(at 0 -19.05 0)
			(show_name yes)
			(do_not_autoplace no)
			(hide yes)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property \"Power Rating\" \"{power_rating}\"
			(at 0 -20.955 0)
			(show_name yes)
			(do_not_autoplace no)
			(hide yes)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property \"Package\" \"{package}\"
			(at 0 -22.86 0)
			(show_name yes)
			(do_not_autoplace no)
			(hide yes)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property \"Series\" \"{series}\"
			(at 0 -24.765 0)
			(show_name yes)
			(do_not_autoplace no)
			(hide yes)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property \"Value Code\" \"{value_code}\"
			(at 0 -26.67 0)
			(show_name yes)
			(do_not_autoplace no)
			(hide yes)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
"""


@dataclass(frozen=True)
class SeriesConfig:
    name: str
    package: str
    footprint: str
    datasheet: str
    manufacturer: str
    tolerance: str
    voltage_rating: str
    power_rating: str
    mpn_template: str
    description_template: str
    base_symbol: str
    min_ohms: float
    max_ohms: float
    default_preset: str
    value_display_format: str


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_resistance_token(token: str) -> float:
    cleaned = token.strip().upper().replace("OHMS", "R").replace("OHM", "R").replace("Ω", "R")
    cleaned = cleaned.replace(" ", "")
    if not cleaned:
        raise ValueError("empty resistance value")

    if re.fullmatch(r"\d+(?:\.\d+)?", cleaned):
        return float(cleaned)

    match = re.fullmatch(r"(?:(\d+(?:\.\d+)?)?)([RKM])(?:(\d+)?)", cleaned)
    if not match:
        raise ValueError(f"unsupported resistance value: {token}")

    integer_part = match.group(1) or "0"
    separator = match.group(2)
    fractional_part = match.group(3) or ""
    combined = f"{integer_part}.{fractional_part}" if fractional_part else integer_part
    factor = {"R": 1.0, "K": 1_000.0, "M": 1_000_000.0}[separator]
    return float(combined) * factor


def format_resistance_label_iec(ohms: float) -> str:
    if ohms == 0:
        return "0R"

    suffix = "R"
    scale = 1.0
    if ohms >= 1_000_000:
        suffix = "M"
        scale = 1_000_000.0
    elif ohms >= 1_000:
        suffix = "K"
        scale = 1_000.0

    scaled = ohms / scale
    text = f"{scaled:.3g}".upper()
    if "E" in text:
        text = f"{scaled:.6f}".rstrip("0").rstrip(".")

    if "." in text:
        return text.replace(".", suffix)
    return f"{text}{suffix}"


def format_resistance_label_decimal(ohms: float) -> str:
    if ohms == 0:
        return "0R"

    suffix = "R"
    scale = 1.0
    if ohms >= 1_000_000:
        suffix = "M"
        scale = 1_000_000.0
    elif ohms >= 1_000:
        suffix = "K"
        scale = 1_000.0

    scaled = ohms / scale
    text = f"{scaled:.3g}".upper()
    if "E" in text:
        text = f"{scaled:.6f}".rstrip("0").rstrip(".")
    return f"{text}{suffix}"


def format_resistance_display(ohms: float, display_format: str) -> str:
    if display_format == "decimal":
        return format_resistance_label_decimal(ohms)
    return format_resistance_label_iec(ohms)


def resistance_value_code(label: str) -> str:
    return label.replace(" ", "")


def build_resistance_values(preset: str, min_ohms: float, max_ohms: float) -> list[tuple[float, str]]:
    base_values = {"E12": E12_BASE, "E24": E24_BASE}.get(preset.upper())
    if base_values is None:
        raise ValueError(f"unsupported preset: {preset}")

    values: list[tuple[float, str]] = []
    seen: set[str] = set()
    if min_ohms <= 0 <= max_ohms:
        seen.add("0R")
        values.append((0.0, "0R"))

    for decade in range(0, 8):
        multiplier = 10**decade
        for base in base_values:
            ohms = base * multiplier
            if ohms < min_ohms or ohms > max_ohms:
                continue
            label = format_resistance_label_iec(ohms)
            if label in seen:
                continue
            seen.add(label)
            values.append((ohms, label))

    values.sort(key=lambda item: item[0])
    return values


def parse_value_source(value_args: list[str], value_file: Path | None, preset: str, min_ohms: float, max_ohms: float) -> list[tuple[float, str]]:
    if value_args or value_file is not None:
        tokens: list[str] = []
        for value_arg in value_args:
            tokens.extend(part for part in re.split(r"[;,\s]+", value_arg) if part)
        if value_file is not None:
            tokens.extend(read_lines(value_file))

        values: list[tuple[float, str]] = []
        seen: set[str] = set()
        for token in tokens:
            ohms = parse_resistance_token(token)
            if ohms < min_ohms or ohms > max_ohms:
                raise ValueError(f"value outside supported range: {token}")
            label = format_resistance_label_iec(ohms)
            if label in seen:
                continue
            seen.add(label)
            values.append((ohms, label))
        values.sort(key=lambda item: item[0])
        return values

    return build_resistance_values(preset, min_ohms, max_ohms)


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


def build_symbol_block(series: SeriesConfig, ohms: float, value_code_label: str) -> str:
    value_code = resistance_value_code(value_code_label)
    display_value = format_resistance_display(ohms, series.value_display_format)
    mpn = series.mpn_template.format(value_code=value_code, value=display_value, series=series.name)
    description = series.description_template.format(
        value=display_value,
        value_code=value_code,
        series=series.name,
        package=series.package,
        tolerance=series.tolerance,
        voltage_rating=series.voltage_rating,
        power_rating=series.power_rating,
    )

    properties = "\n".join(
        [
            property_block("Reference", "R", 1.905, show_name="no", hidden=False, do_not_autoplace="yes"),
            property_block("Value", display_value, -1.905, show_name="no", hidden=False, do_not_autoplace="yes"),
            property_block("Footprint", series.footprint, -6.985),
            property_block("Datasheet", series.datasheet, -9.525),
            property_block("Description", description, 0),
            property_block("Manufacturer", series.manufacturer, -13.335),
            property_block("MFN", series.manufacturer, -14.2875),
            property_block("MPN", mpn, -15.24),
            property_block("Tolerance", series.tolerance, -17.145),
            property_block("Voltage Rating", series.voltage_rating, -19.05),
            property_block("Power Rating", series.power_rating, -20.955),
            property_block("Package", series.package, -22.86),
            property_block("Series", series.name, -24.765),
            property_block("Value Code", value_code, -26.67),
        ]
    )

    return (
        f"\t(symbol \"{mpn}\"\n"
        f"\t\t(extends \"{series.base_symbol}\")\n"
        f"{properties}\n"
        f"\t\t(embedded_fonts no)\n"
        f"\t)"
    )


def no_mount_symbol_name(series_name: str) -> str:
    match = re.match(r"^(RC\d+)", series_name)
    if match:
        return f"{match.group(1)}_N.M."
    return f"{series_name}_N.M."


def build_no_mount_symbol(series: SeriesConfig) -> str:
    properties = "\n".join(
        [
            property_block("Reference", "R", 1.905, show_name="no", hidden=False, do_not_autoplace="yes"),
            property_block("Value", "N.M.", -1.905, show_name="no", hidden=False, do_not_autoplace="yes"),
            property_block("Footprint", series.footprint, -6.985),
            property_block("Datasheet", series.datasheet, -9.525),
            property_block("Description", "No mount resistor", 0),
            property_block("Manufacturer", series.manufacturer, -13.335),
            property_block("MFN", series.manufacturer, -14.2875),
            property_block("MPN", "N.M.", -15.24),
            property_block("Tolerance", series.tolerance, -17.145),
            property_block("Voltage Rating", series.voltage_rating, -19.05),
            property_block("Power Rating", series.power_rating, -20.955),
            property_block("Package", series.package, -22.86),
            property_block("Series", series.name, -24.765),
            property_block("Value Code", "N.M.", -26.67),
        ]
    )

    return (
        f"\t(symbol \"{no_mount_symbol_name(series.name)}\"\n"
        f"\t\t(extends \"{series.base_symbol}\")\n"
        f"{properties}\n"
        f"\t\t(embedded_fonts no)\n"
        f"\t)"
    )


def build_library(series: SeriesConfig, values: list[tuple[float, str]]) -> str:
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
            property_block("Reference", "R", 1.905, show_name="no", hidden=False, do_not_autoplace="yes"),
            property_block("Value", "XXXX", -1.905, show_name="no", hidden=False, do_not_autoplace="yes"),
            property_block("Footprint", series.footprint, -6.985),
            property_block("Datasheet", series.datasheet, -9.525),
            property_block(
                "Description",
                series.description_template.format(
                    value="XXXX",
                    value_code="XXXX",
                    series=series.name,
                    package=series.package,
                    tolerance=series.tolerance,
                    voltage_rating=series.voltage_rating,
                    power_rating=series.power_rating,
                ),
                0,
            ),
            property_block("Manufacturer", series.manufacturer, -13.335),
            property_block("MFN", series.manufacturer, -14.2875),
            property_block("Tolerance", series.tolerance, -15.24),
            property_block("Voltage Rating", series.voltage_rating, -17.145),
            property_block("Power Rating", series.power_rating, -19.05),
            property_block("Package", series.package, -20.955),
            property_block("Series", series.name, -22.86),
        ]
    )

    base_symbol = BASE_SYMBOL_TEMPLATE.format(base_symbol=series.base_symbol, properties=base_properties)
    no_mount_symbol = build_no_mount_symbol(series)
    variant_symbols = [build_symbol_block(series, ohms, label) for ohms, label in values]
    return "\n".join([header, base_symbol, no_mount_symbol, *variant_symbols, ")\n"])


def load_series_config(config: dict, series_name: str) -> SeriesConfig:
    series_data = config["series"][series_name]
    global_defaults = config["defaults"]
    return SeriesConfig(
        name=series_name,
        package=series_data.get("package", global_defaults["package"]),
        footprint=series_data.get("footprint", global_defaults["footprint"]),
        datasheet=series_data.get("datasheet", global_defaults["datasheet"]),
        manufacturer=series_data.get("manufacturer", global_defaults["manufacturer"]),
        tolerance=series_data.get("tolerance", global_defaults["tolerance"]),
        voltage_rating=series_data.get("voltage_rating", global_defaults["voltage_rating"]),
        power_rating=series_data.get("power_rating", global_defaults["power_rating"]),
        mpn_template=series_data.get("mpn_template", global_defaults["mpn_template"]),
        description_template=series_data.get("description_template", global_defaults["description_template"]),
        base_symbol=series_data.get("base_symbol", global_defaults["base_symbol"]),
        min_ohms=float(series_data.get("min_ohms", global_defaults["min_ohms"])),
        max_ohms=float(series_data.get("max_ohms", global_defaults["max_ohms"])),
        default_preset=series_data.get("default_preset", global_defaults["default_preset"]),
        value_display_format=series_data.get("value_display_format", global_defaults.get("value_display_format", "iec")),
    )


def resolve_path(path_text: str | None, default_path: Path) -> Path:
    if not path_text:
        return default_path
    return Path(path_text)


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Generate KiCad resistor symbol libraries from a value list or E-series preset.")
    parser.add_argument("--config", default=str(script_dir / "kicad_resistor_config.json"), help="Path to the JSON config file.")
    parser.add_argument("--series", default=None, help="Series name from the config file. Defaults to the config's default_series.")
    parser.add_argument("--preset", choices=("E12", "E24"), default=None, help="Generate an E12 or E24 value set.")
    parser.add_argument("--values", action="append", default=[], help="Custom value list. Comma, semicolon, or whitespace separated.")
    parser.add_argument("--values-file", default=None, help="Text file with one value per line.")
    parser.add_argument("--output", default=None, help="Output .kicad_sym file path.")
    parser.add_argument("--values-output", default=None, help="Optional companion value list output path.")
    parser.add_argument("--no-values-output", action="store_true", help="Do not write the companion generated values text file.")
    parser.add_argument("--value-display-format", choices=("iec", "decimal"), default=None, help="Schematic value text format: IEC style (3K3) or decimal style (3.3K).")
    args = parser.parse_args()

    config = load_json(Path(args.config))
    series_name = args.series or config["generator"]["default_series"]
    series = load_series_config(config, series_name)
    if args.value_display_format:
        series = SeriesConfig(
            name=series.name,
            package=series.package,
            footprint=series.footprint,
            datasheet=series.datasheet,
            manufacturer=series.manufacturer,
            tolerance=series.tolerance,
            voltage_rating=series.voltage_rating,
            power_rating=series.power_rating,
            mpn_template=series.mpn_template,
            description_template=series.description_template,
            base_symbol=series.base_symbol,
            min_ohms=series.min_ohms,
            max_ohms=series.max_ohms,
            default_preset=series.default_preset,
            value_display_format=args.value_display_format,
        )
    preset = args.preset or series.default_preset

    values_file = Path(args.values_file) if args.values_file else None
    values = parse_value_source(args.values, values_file, preset, series.min_ohms, series.max_ohms)

    output_path = resolve_path(args.output, script_dir / f"{series.name}.generated.kicad_sym")
    values_output_path = resolve_path(args.values_output, output_path.with_suffix(".values.txt"))

    output_path.write_text(apply_kicad(build_library(series, values), load_cache()), encoding="utf-8", newline="\n")
    if not args.no_values_output:
        values_output_path.write_text("\n".join(label for _, label in values) + "\n", encoding="utf-8", newline="\n")

    print(f"Wrote {output_path}")
    if not args.no_values_output:
        print(f"Wrote {values_output_path}")
    print(f"Generated {len(values)} values for {series.name} using {('custom list' if args.values or args.values_file else preset)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
