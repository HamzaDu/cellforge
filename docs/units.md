# Units convention

Every CellForge function uses the units below, and the unit is written into the argument name
(`loading_mg_cm2`, `thickness_um`, `capacity_mah`). If your number comes in a different unit
(supplier datasheet, paper, cycler export), convert it first with `cellforge.units`.

## Standard units

| Quantity | Unit | Argument suffix | Notes |
|---|---|---|---|
| Coating loading | mg/cm² | `_mg_cm2` | One side of the foil |
| Coating / foil / separator thickness | µm | `_um` | Coating only, excluding the current collector |
| Electrode and cell dimensions | mm | `_mm` | Width, length, diameter, cell thickness |
| Area | cm² | `_cm2` | One electrode face |
| Volume | cm³ (= mL) | `_cm3` | |
| Density (true, coating, tap) | g/cm³ | `_g_cm3` | |
| Specific capacity | mAh/g | `_mah_g` | Per gram of **active material** |
| Areal capacity | mAh/cm² | `_mah_cm2` / `areal_capacity` | Per coated face |
| Capacity | mAh | `_mah` | Divide by 1000 for Ah |
| Current | mA | `_ma` | Positive = charge |
| Time | s | `_s` | |
| Voltage | V | `_v` | vs Li/Li⁺ for half-cell materials |
| Energy | Wh (cell), mWh (cycler data) | `_wh`, `_mwh` | |
| Specific energy / energy density | Wh/kg, Wh/L | | |
| Mass | g (cell parts), mg (active mass in coin cells) | `_g`, `_mg` | |
| Price | per kg, in the stated currency | `price_per_kg` + `currency` | Currencies are never converted automatically |

## Fractions, not percentages

Porosity, weight fractions, active material fraction and efficiencies are **fractions from 0 to 1**:
write `0.30`, not `30`. Functions reject values above 1 where a fraction is expected, so a percent
typed by mistake gives an error instead of a wrong answer. Convert with
`percent_to_fraction(30) -> 0.30`.

## Converting

```python
from cellforge.units import convert, percent_to_fraction, charge_to_energy

convert(250, "g/m2", "mg/cm2")       # 25.0   supplier loading -> CellForge
convert(1.1, "g/cc", "g/cm3")        # 1.1
convert(3.2, "Ah", "mAh")            # 3200
convert(12, "µm", "mm")              # 0.012
convert(18, "per_kg", "per_t")       # 18000  price per tonne
percent_to_fraction(96)              # 0.96
charge_to_energy(900, 3.7)           # 3.33 Wh (needs a voltage, so it isn't a plain convert)
```

Unit spellings are forgiving (`µm`/`um`, `cm²`/`cm2`/`cm^2`, `g/cc`/`g/cm³`). Converting between
different quantities (e.g. mAh to Wh, or mg to mm) raises an error.
