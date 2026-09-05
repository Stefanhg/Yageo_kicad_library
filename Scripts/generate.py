"""Generate the default library set selected by each component config."""

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def generation_commands(output_dir: Path) -> list[list[str]]:
    commands = []
    for kind in ("resistor", "capacitor"):
        directory = ROOT / "Scripts" / f"{kind.capitalize()}s" / "kicad"
        config_path = directory / f"kicad_{kind}_config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        defaults = config["generator"]
        for series, filename in defaults["default_libraries"].items():
            if series not in config["series"]:
                raise ValueError(f"Unknown default series {series} in {config_path}")
            if Path(filename).name != filename or not filename.endswith(".kicad_sym"):
                raise ValueError(f"Expected a .kicad_sym filename for {series}")
            preset = config["series"][series].get("default_preset", defaults["default_preset"])
            commands.append([
                sys.executable, str(directory / f"kicad_{kind}_generator.py"),
                "--config", str(config_path), "--series", series,
                "--preset", preset, "--output", str(output_dir / filename),
                "--no-values-output" if kind == "resistor" else "--no-csv-output",
            ])
    return commands


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "Libraries" / "Kicad")
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    commands = generation_commands(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for command in commands:
        subprocess.run(command, check=True, cwd=ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
