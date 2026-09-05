# Capacitor KiCad Scripts

This folder contains the KiCad Yageo MLCC capacitor generator.

## Files

- [kicad_capacitor_generator.py](kicad_capacitor_generator.py)
- [kicad_capacitor_config.json](kicad_capacitor_config.json)
- [yageo_mlcc_research.md](yageo_mlcc_research.md)
- [yageo_mlcc_exposed_values.md](yageo_mlcc_exposed_values.md)

## Usage

Run from repo root (defaults to all supported series in config):

```powershell
python Scripts/Capacitors/kicad/kicad_capacitor_generator.py --preset verified_baseline
```

Generate only specific series:

```powershell
python Scripts/Capacitors/kicad/kicad_capacitor_generator.py --series CC0402 --series CC0603 --preset core_decoupling
```

Include policy candidates (unverified MPNs):

```powershell
python Scripts/Capacitors/kicad/kicad_capacitor_generator.py --series CC1206 --preset core_decoupling --include-unverified
```

## Verification Model

Each part row in the config carries `verification` metadata:

- `repo_observed`: observed in existing repository libraries
- `skill_example`: explicit example in selector policy skill
- `policy_candidate`: policy-derived candidate, not yet source-validated here

By default, the generator excludes rows where only a policy candidate is present.

## Output

The generator writes:

- `<SERIES>.generated.kicad_sym`
- `<SERIES>.generated.manifest.csv`

The manifest CSV captures selected MPN, candidate MPN, dielectric, tolerance, voltage, and verification status for each generated symbol.