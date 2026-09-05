# EagleCadLibraries

This repository contains resistor and capacitor libraries for Eagle and KiCad.

The repository is now organized into two top-level areas:

- [Libraries](Libraries)
- [Scripts](Scripts)

## Layout

```text
Libraries/
	Kicad/
		RC0402FR.kicad_sym
		RC0603FR.kicad_sym
		RC1206.kicad_sym
		RC0402FR-RESC1005X40N.kicad_mod
		RC0603FR-RESC1608X60N.kicad_mod
		CC0402-CAPC1005X55N.kicad_mod
		CC0603-CAPC1608X90N.kicad_mod
	Eaglecad/
		legacy Eagle libraries
	3D/
		Resistors/
			RC0402.STEP
			RC0603.STEP
			RC0805.STEP
			RC1206.STEP

Scripts/
	generate.bat
	Resistors/
		kicad/
			kicad_resistor_generator.py
			kicad_resistor_config.json
			README.md
		eaglecad/
			RCXXXX_SCRIPT.py
			README.md
	Capacitors/
		kicad/
			README.md
		eaglecad/
			CCXXXX_SCRIPT.py
			README.md
```

The root of the repository no longer carries duplicated library copies. The structured copies are now under [Libraries](Libraries).

## Capacitor Generation Note

Capacitor library generation is not a simple formula or naming exercise. YAGEO MLCC part availability, voltage ratings, dielectric choices, and package-specific high-capacitance limits change over time, so generated capacitor MPNs must be validated against current manufacturer data to be trustworthy.

To generate capacitors correctly, AI is required for proper results. The library selection process needs AI-assisted validation to avoid inventing unverifiable MPNs or choosing a part that is technically wrong for the package, voltage, or dielectric class.

## How To Use The KiCad Generator

The active KiCad resistor generator is [Scripts/Resistors/kicad/kicad_resistor_generator.py](Scripts/Resistors/kicad/kicad_resistor_generator.py).

If you just want the default generated library set, run [Scripts/generate.bat](Scripts/generate.bat).

It can generate resistor symbols from:

- A custom value list supplied on the command line.
- A text file containing one value per line.
- An E-series preset: `E12` or `E24`.

### Generate A Preset Library

```powershell
python Scripts/Resistors/kicad/kicad_resistor_generator.py --preset E24
```

Use `E12` if you want the smaller standard series:

```powershell
python Scripts/Resistors/kicad/kicad_resistor_generator.py --preset E12
```

### Generate From A Custom Value List

```powershell
python Scripts/Resistors/kicad/kicad_resistor_generator.py --values 1R,4R7,10K,100K
```

You can also read from a file:

```powershell
python Scripts/Resistors/kicad/kicad_resistor_generator.py --values-file values.txt
```

### Pick A Different Series

The default series is `RC0603FR`. To use another supported series from the config:

```powershell
python Scripts/Resistors/kicad/kicad_resistor_generator.py --series RC0402FR --preset E24
```

## What To Configure

Edit [Scripts/Resistors/kicad/kicad_resistor_config.json](Scripts/Resistors/kicad/kicad_resistor_config.json) if you want to change:

- Default series.
- Default preset.
- Footprint mapping.
- Datasheet link.
- Manufacturer name.
- Tolerance.
- Voltage rating.
- Power rating.
- The MPN naming template.
- The description template.
- The supported resistance range for a series.

If you want a different value naming scheme, that file is the place to do it. The script itself stays generic.

## Output

By default the script writes two files next to itself:

- `RC0603FR.generated.kicad_sym`
- `RC0603FR.generated.values.txt`

You can override both paths with `--output` and `--values-output`.

The `.kicad_sym` file contains the generated symbol library. The `.values.txt` file is a plain list of the emitted values, which is useful if you want to reuse the same set elsewhere.

## Supported Series

The current config includes these resistor series entries:

- RC0100FR
- RC0201FR
- RC0402FR
- RC0603FR
- RC0805FR
- RC1206FR
- RC1210FR

The default RC0603 entry is the one currently wired for actual generation. The others are present so the naming and metadata scheme can be reused later.

## Notes

- LCSC number lookup, the persistent MPN mapping table, and offline jlcparts database support are documented in [Scripts/LCSC/README.md](Scripts/LCSC/README.md). Both KiCad generators reuse cached LCSC mappings automatically.

- The KiCad library copies live under [Libraries/Kicad](Libraries/Kicad).
- The Eagle library copies live under [Libraries/Eaglecad](Libraries/Eaglecad).
- The old Eagle material is still present in the repo, but the KiCad generator is the path to extend going forward.
