---
name: yageo-cc-mlcc-selector
description: Select aligned YAGEO CC-series MLCC part numbers for 0402/0603/0805/1206, prioritizing common numbering, high voltage rating, and useful high-capacitance C×V coverage.
---

# YAGEO CC MLCC Selector

## Goal

Generate a compact, internally consistent library of YAGEO `CC` MLCC part numbers for:

- `CC0402`
- `CC0603`
- `CC0805`
- `CC1206`

The library should optimize, in this order:

1. **Use a common/aligned part-number family wherever practical.**
2. **Use the highest useful voltage rating within that family.**
3. **Prefer X7R for the normal range.**
4. **At high capacitance, allow X5R when it gives materially better capacitance × voltage coverage.**
5. **Avoid Y5V.**
6. **Use ±10% (`K`) as the normal tolerance.**
7. Produce exactly **one recommended MPN per package size + capacitance value**, unless the caller explicitly requests alternatives.

This skill is intentionally not a pure E-series generator. MLCC availability has holes and voltage/capacitance tradeoffs, so every generated MPN must be validated against a YAGEO source before being emitted as final.

---

# Core selection philosophy

## Canonical aligned family

For ordinary values, prefer the familiar general-purpose X7R, ±10%, 50 V family:

```text
CC<size>KRX7R9BB<cap-code>
```

Examples:

```text
CC0402KRX7R9BB332
CC0603KRX7R9BB104
CC0805KRX7R9BB473
```

Interpret this as the **backbone family**, not a guarantee that every capacitance exists at 50 V.

Keep these fields stable whenever possible:

```text
CC<size> K R X7R <voltage-code> BB <cap-code>
          ^   ^
          |   dielectric
          ±10%
```

Do not invent a part number just because the syntax looks valid.

## Voltage codes commonly encountered

Use these only after validating that the resulting MPN exists:

```text
5 = 6.3 V
6 = 10 V
7 = 16 V
8 = 25 V
9 = 50 V
0 = 100 V
```

Higher-voltage codes may exist, but they are outside the normal backbone and must be source-validated individually.

---

# The important breakpoint: 1 µF

Treat **1 µF as the start of the high-capacitance decision region**.

Below 1 µF, a 50 V X7R ±10% backbone is generally the cleanest way to keep numbering aligned across the four target sizes.

At 1 µF and above, the maximum useful voltage diverges sharply by package and dielectric:

| Capacitance | 0402 | 0603 | 0805 | 1206 |
|---|---:|---:|---:|---:|
| 1 µF | X5R 25 V; X7R 6.3 V | X7R/X5R 50 V | X7R/X5R 50 V | **X7R 100 V** |
| 2.2 µF | X5R 25 V | **X5R 50 V** | **X5R 50 V** | X7R/X5R 50 V |
| 4.7 µF | X5R 16 V | X5R 25 V | **X5R 50 V** | X7R/X5R 50 V |
| 10 µF | X5R 10 V | X5R 25 V | **X5R 50 V** | **X5R 50 V** |
| 22 µF | X5R 6.3 V | X5R 16 V | X5R 10 V | X5R 25 V / X7R 16 V |
| 47 µF | — | X5R 4 V | X5R 10 V | X5R 16 V |
| 100 µF | — | — | X5R 6.3 V | X5R 6.3 V |

The table above is the high-capacitance seed table from YAGEO's published CC high-capacitance selection guide. Current individual YAGEO product pages must be checked before finalizing a library.

---

# Recommended rules by package

## 0402

### Normal region

Prefer:

```text
CC0402KRX7R9BB<cap>
```

for values where a 50 V X7R ±10% part actually exists.

Do not force 50 V once capacitance makes it unavailable.

### High-cap region

Use these target ceilings:

```text
1.0 µF  -> prefer 25 V X5R if maximizing useful rating
2.2 µF  -> 25 V X5R
4.7 µF  -> 16 V X5R
10  µF  -> 10 V X5R
22  µF  -> 6.3 V X5R
```

For 1 µF, X7R exists at only 6.3 V in the cited high-cap table, so X5R 25 V is usually the better generic-library choice if voltage coverage matters more than keeping X7R.

---

## 0603

### Normal region

The preferred aligned backbone is:

```text
CC0603KRX7R9BB<cap>
```

50 V X7R ±10%.

YAGEO also has some 100 V X7R 0603 parts, for example `CC0603KRX7R0BB104` (100 nF, 100 V).

However, do **not** automatically move the whole 0603 library to 100 V. Use 100 V only where it is validated and doing so does not create an unnecessarily fragmented library.

If the objective is maximum voltage regardless of uniformity, prefer the validated 100 V part.

If the objective is the cleanest aligned library, prefer the 50 V backbone.

### High-cap region

```text
1.0 µF  -> 50 V X7R or X5R; prefer X7R
2.2 µF  -> 50 V X5R
4.7 µF  -> 25 V X5R
10  µF  -> 25 V X5R
22  µF  -> 16 V X5R
47  µF  -> 4 V X5R
```

This is where the simple `...X7R9BB...` pattern starts to break.

---

## 0805

### Normal region

Prefer the 50 V X7R ±10% backbone:

```text
CC0805KRX7R9BB<cap>
```

100 V X7R parts exist for some smaller capacitances, but use them as upgrades only when validated.

### High-cap region

For generic coverage, X5R gives excellent voltage density:

```text
1.0 µF  -> 50 V; prefer X7R
2.2 µF  -> 50 V X5R
4.7 µF  -> 50 V X5R
10  µF  -> 50 V X5R
22  µF  -> 10 V X5R
47  µF  -> 10 V X5R
100 µF  -> 6.3 V X5R
```

This means 0805 is particularly clean through 10 µF if X5R is acceptable: a 50 V rating can be retained over a wide high-cap range.

---

## 1206

### Normal region

Use X7R ±10%.

For values where 100 V exists and maximum voltage is valuable, prefer:

```text
CC1206KRX7R0BB<cap>
```

If a broad, common 50 V family is more important than absolute voltage, use:

```text
CC1206KRX7R9BB<cap>
```

### High-cap region

```text
1.0 µF  -> 100 V X7R
2.2 µF  -> 50 V X7R or X5R; prefer X7R
4.7 µF  -> 50 V X7R or X5R; prefer X7R
10  µF  -> 50 V X5R (X7R only 25 V)
22  µF  -> 25 V X5R (X7R 16 V)
47  µF  -> 16 V X5R
100 µF  -> 6.3 V X5R
```

---

# Selection algorithm

For each `(package, capacitance)`:

```text
1. Find actual YAGEO CC candidates for the requested package and capacitance.

2. Discard:
   - wrong package
   - Y5V, unless explicitly requested
   - tolerance worse than ±20%
   - specialty families that are not desired by the caller
   - obsolete/unverifiable MPNs

3. Prefer ±10% (`K`).

4. Establish whether the capacitance is in the normal or high-cap region:
   normal: C < 1 µF
   high-cap: C >= 1 µF

5. Normal region:
   a. Prefer X7R.
   b. Prefer an MPN matching the package's common backbone.
   c. Among equally aligned candidates, choose the highest voltage.
   d. Do not switch to X5R merely to gain a small voltage advantage.

6. High-cap region:
   a. Compare X7R and X5R.
   b. Prefer X7R if voltage is equal or close.
   c. Prefer X5R when it materially improves usable C×V coverage.
   d. Use the package tables in this skill as the initial target.
   e. Validate the exact MPN.

7. If a candidate is a higher-voltage version but changes only the voltage-code
   digit while keeping the rest of the family aligned, that is a low-cost
   exception and is normally acceptable.

8. Emit one preferred MPN.
```

---

# Ranking function

Use a lexicographic ranking rather than one weighted score.

For the normal region:

```python
rank = (
    is_valid_current_yageo_part,
    is_x7r,
    is_10_percent,
    matches_backbone_except_voltage,
    voltage_rating,
)
```

For the high-cap region:

```python
rank = (
    is_valid_current_yageo_part,
    is_10_or_20_percent,
    useful_voltage_rating,
    dielectric_quality,   # X7R > X5R > Y5V
    numbering_alignment,
)
```

Do not maximize voltage so aggressively that it replaces a broad coherent family with unrelated specialty parts.

---

# Capacitance code

Standard three-digit capacitor coding:

```text
first two digits = significant digits
third digit      = number of added zeros in pF
```

Examples:

```text
100 pF  -> 101
1 nF    -> 102
10 nF   -> 103
100 nF  -> 104
1 µF    -> 105
2.2 µF  -> 225
4.7 µF  -> 475
10 µF   -> 106
22 µF   -> 226
```

Sub-10 pF values can use forms such as `4R7`; do not synthesize these unless the exact part is verified.

---

# Validation requirements

Before returning an MPN as final:

1. Search YAGEO's own current product/specsheet page for the exact MPN.
2. Confirm:
   - package
   - capacitance
   - tolerance
   - dielectric
   - voltage
   - standard/general-purpose family
3. If YAGEO's source cannot confirm it, do not silently invent it.
4. Distributor pages may be used as a secondary check, not as the primary source.
5. If the historical selection table and current YAGEO product page disagree, use the current YAGEO product page.

---

# Output format

For generator/library work, return compact machine-readable rows:

```text
package,capacitance,mpn,dielectric,tolerance,voltage
0603,100nF,CC0603KRX7R0BB104,X7R,10%,100V
0603,1uF,<validated MPN>,X7R,10%,50V
0603,2.2uF,<validated MPN>,X5R,10%,50V
```

When a preferred value cannot be verified:

```text
0603,4.7uF,UNVERIFIED,X5R,10%,25V
```

Never fabricate the missing MPN.

---

# Generator implementation advice

A small Python generator is appropriate for:

- E-series / preferred capacitance candidate generation
- capacitance-code conversion
- package iteration
- sorting/ranking already validated candidates
- output CSV/JSON/YAML

A generator should **not** infer product existence from the MPN grammar alone.

Use a curated availability table, scraped/exported YAGEO data, or agent-assisted validation as the source of truth.

Suggested data model:

```python
Part(
    package="0603",
    capacitance_f=2.2e-6,
    dielectric="X5R",
    tolerance_pct=10,
    voltage_v=50,
    mpn="...",
    source="yageo",
    verified=True,
)
```

Then select with the rules in this skill.

---

# Sources used to establish this policy

Primary YAGEO high-capacitance CC selection guide:

https://yageogroup.com/content/Resource%20Library/Product%20Guide-Catalog/yageo_High-20Capacitance-20MLCCs_2016_19050911_141.pdf

Current YAGEO examples confirming active/common families:

- `CC0402KRX7R9BB332` — 0402, 3.3 nF, X7R, 10%, 50 V
- `CC0603KRX7R0BB104` — 0603, 100 nF, X7R, 10%, 100 V
- `CC0603MRX7R9BB104` — 0603, 100 nF, X7R, 20%, 50 V
- `CC0805KRX7R9BB473` — 0805, 47 nF, X7R, 10%, 50 V
- `CC0402KRX7R5BB105` — 0402, 1 µF, X7R, 10%, 6.3 V

The historical high-cap table is useful for topology and breakpoint decisions, but final MPNs must always be revalidated against current YAGEO product/specsheet data.
