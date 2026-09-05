# Resistor KiCad Scripts

This folder contains the active KiCad resistor generator.

## Files

- [kicad_resistor_generator.py](kicad_resistor_generator.py)
- [kicad_resistor_config.json](kicad_resistor_config.json)

## Usage

Run the generator from the repo root or this folder:

```powershell
python Scripts/Resistors/kicad/kicad_resistor_generator.py --preset E24
```

Edit the JSON config file to change series defaults, footprints, datasheets, value naming, or exposed KiCad properties.