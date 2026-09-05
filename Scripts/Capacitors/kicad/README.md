# Capacitor KiCad Scripts

This folder contains the KiCad Yageo MLCC capacitor generator.

## Files

- [kicad_capacitor_generator.py](kicad_capacitor_generator.py)
- [kicad_capacitor_config.json](kicad_capacitor_config.json)
- [yageo_mlcc_research.md](yageo_mlcc_research.md)
- [yageo_mlcc_exposed_values.md](yageo_mlcc_exposed_values.md)

## Usage

The default preset is now `E24`, requesting 193 capacitances from 1 pF through
100 uF. Only database-validated matches are emitted, so package counts differ.
Edit `presets.E24.min_value` and `max_value` to change the range. Range presets
support `series: "E12"` or `"E24"`; explicit value-list presets still work.
`Scripts/generate.bat` uses the configured default automatically.

Run from repo root (defaults to all supported series in config):

```powershell
python Scripts/Capacitors/kicad/kicad_capacitor_generator.py
```

Generate only specific series:

```powershell
python Scripts/Capacitors/kicad/kicad_capacitor_generator.py --series CC0402 --series CC0603 --preset core_decoupling
```

Use an extracted database in a different location:

```powershell
python Scripts/Capacitors/kicad/kicad_capacitor_generator.py --database D:/Parts/cache.sqlite3
```

## Verification Model

Generation reads `Data/LCSC/jlcparts/cache.sqlite3` read-only, including when
called by `Scripts/generate.bat`. If missing, the published snapshot is
automatically downloaded and extracted (requires 7-Zip and several GB of disk
space). Subsequent runs use it offline. Override the location with `--database` or
`generator.database` in the config (relative to the repository root).

The first lookup creates a compact `cache.sqlite3.capacitors.json` beside the
database. All packages and subsequent runs reuse it, avoiding repeated scans
of the full database. It rebuilds automatically when the source path, size or
modification time changes, or the cache is missing/unreadable. The source
SQLite file remains read-only. The default cache location is ignored by Git.

The preset or `--values` supplies requested capacitances. For each value,
the generator finds Yageo CC catalogue MPNs for that package and verifies
capacitance, tolerance, dielectric and voltage against the database attributes
and MPN codes. Paper and embossed reel codes are supported. Incomplete,
conflicting and ambiguous records are excluded. Missing values are reported.

There is no curated part list or pre-validation status in the config.
Selection uses only database-validated records and prefers X7R below 1 uF,
tolerance closest to 10%, then voltage and
dielectric quality. One part is emitted per requested value, with its `LCSC`
field, database datasheet link and `Verification=lcsc_database`.

Validation refers to the local catalogue snapshot, not live stock or a new
manufacturer datasheet review. Unverified parts cannot be emitted.
The preset name `verified_baseline` is retained for compatibility; it is only
a list of requested values, not a list of pre-validated parts.

## Output

The generator writes:

- `<SERIES>.generated.kicad_sym`
- `<SERIES>.generated.manifest.csv`

The manifest CSV captures selected MPN, candidate MPN, dielectric, tolerance, voltage, and verification status for each generated symbol.
