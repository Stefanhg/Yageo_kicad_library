# LCSC mapping

Python 3.10+; uses the standard library. Run commands from the repository root.
Both KiCad `.kicad_sym` MPN properties and Eagle `.lbr` MPN attributes are supported.
The default scan includes `Libraries/` and the checked-in `Scripts/**/*.generated.kicad_sym`
outputs. Legacy Yageo symbols with the full RC/CC MPN as their symbol name are also supported.

## Download and use the public database

```powershell
python Scripts/LCSC/lcsc.py download
python Scripts/LCSC/lcsc.py sync --database Data/LCSC/jlcparts/cache.sqlite3 --apply
```

The download command retrieves the [jlcparts published snapshot](https://yaqwsx.github.io/jlcparts/data/cache.zip)
and its `cache.z01`, `cache.z02`, etc. volumes, then extracts `cache.sqlite3` using
7-Zip (on PATH or installed in `C:\Program Files\7-Zip`). The download and extracted
database can occupy multiple GB; the staging archives are removed after extraction.
The database stays at `Data/LCSC/jlcparts/cache.sqlite3`, which is ignored by Git.
It is downloaded only when you run `download`, not on every lookup.

No LCSC or JLCPCB API credentials are needed to consume this published copy.
The credentials in the upstream workflow are used by its maintainers to refresh
the source data. This script neither runs that workflow nor calls those authenticated APIs.
There is no need to clone jlcparts or build its frontend. Browser IndexedDB storage
is separate from this explicitly downloaded SQLite file.

To use a database already on your computer:

```powershell
python Scripts/LCSC/lcsc.py sync --database "D:\Parts\cache.sqlite3" --apply
```

Supports the upstream `source-db-v2` (`jlc_components`) and legacy `v_components`
schemas. It opens SQLite read-only and scans once for all new MPNs.

## Smaller online alternative

```powershell
python Scripts/LCSC/lcsc.py sync --apply
```

This uses the token-free [jlcsearch community API](https://github.com/tscircuit/jlcsearch),
with a half-second delay between requests. `--limit 10` limits the number of searches.
It searches only MPNs not already resolved or recorded as unresolved.
Network errors remain retryable and are never treated as a missing part.

## Local mapping table and repeat runs

`Data/LCSC/mpn_to_lcsc.csv` is the persistent, Git-tracked mapping table. Each
successful lookup is saved immediately, with MPN, LCSC code, package, manufacturer
when supplied by the source, source name and lookup timestamp. Exact MPN matching
ignores case and surrounding whitespace but preserves suffixes and punctuation.
Multiple exact LCSC codes are reported as ambiguous; no substitute is selected.
Yageo RC/CC package and manufacturer metadata are checked when supplied by the source.
This is an identity lookup, not electrical, lifecycle, stock or datasheet validation.
An absent result in the JLCPCB catalogue does not prove a part is unavailable from LCSC.

`Data/LCSC/search_status.json` tracks unsuccessful searches to avoid repeating them.
To revisit them after downloading a newer database or switching sources:

```powershell
python Scripts/LCSC/lcsc.py sync --database Data/LCSC/jlcparts/cache.sqlite3 --retry-missing --apply
```

Successful mappings are always reused. To recheck one, remove its CSV row and use
`--retry-missing`. Keep the CSV in Git. Run only one sync process at a time.
Existing conflicting LCSC fields stop the write instead of being overwritten.
Generic/template symbols and no-mount entries are skipped; parts need an MPN field
or a full Yageo RC/CC MPN as their KiCad symbol name.

Without `--apply`, searches still update the cache but library edits are previewed.
Use cached mappings without any network or database lookup:

```powershell
python Scripts/LCSC/lcsc.py sync --offline --apply
```

Both active KiCad generators automatically reuse the default mapping table, even
when run directly. Generating libraries performs no network requests.
Optional positional paths restrict which libraries are scanned and updated.

## Verification

```powershell
python -m unittest discover -s Scripts/LCSC -p "test_*.py"
```
