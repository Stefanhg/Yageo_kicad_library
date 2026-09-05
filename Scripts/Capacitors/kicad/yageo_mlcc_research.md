# Yageo CC MLCC Research Notes (2026-09-05)

## Scope

- Series family: Yageo `CC` MLCC
- Target packages: `0402`, `0603`, `0805`, `1206`
- Intended generator outputs: KiCad symbols with one preferred part per exposed capacitance value

## Source Summary

Primary policy source currently available in this repository:

- `.github/skills/yageo-cc-mlcc-selector/SKILL.md`

Direct scraping of current Yageo product pages was attempted, but page content is gated by a cookie wall / dynamic rendering in this environment, so the fetch tool only returned generic shell/404 content.

## Selection Rules Used

- Prefer aligned family where practical: `CC<size>KRX7R9BB<cap-code>`
- Keep `K` (10%) as default tolerance
- Prefer X7R in normal range (`C < 1uF`)
- High-cap region starts at `1uF`:
  - allow X5R when it materially improves available voltage/capacitance coverage
- Avoid Y5V
- Never silently fabricate "verified" parts

## Voltage Code Mapping (Policy)

- `5` => 6.3V
- `6` => 10V
- `7` => 16V
- `8` => 25V
- `9` => 50V
- `0` => 100V

## Verification Status Model

Rows used by the generator are tagged:

- `repo_observed`: MPN exists in current repo libraries
- `skill_example`: MPN appears explicitly in selector skill examples
- `policy_candidate`: candidate derived from policy table, not source-verified here

Generator defaults to `repo_observed` + `skill_example` rows unless `--include-unverified` is set.

## High-Cap Package Guidance (from selector skill)

- 0402: 1uF often constrained in X7R; X5R becomes important above 1uF
- 0603: can hold 50V further into mid-cap values than 0402
- 0805: strong 50V coverage through 10uF with X5R in policy guidance
- 1206: strongest voltage options, including 100V at 1uF in policy guidance

## Notes

- This is a "safe first pass" dataset for generator bring-up.
- As Yageo product-page/API access is added, replace `policy_candidate` rows with fully verified rows.
