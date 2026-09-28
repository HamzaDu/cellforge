# Cycling analysis (`cellforge.cycling`)

Turns raw cycler data into per-cycle results. Plain Python, no extra dependencies.

**Units:** time s · current mA (positive = charge, BioLogic convention) · voltage V · capacity mAh · energy mWh · specific capacity mAh/g.

| Function | What it gives you |
|---|---|
| `integrate_capacity(t, I)` | Total capacity passed (mAh), trapezoidal ∫\|I\|dt |
| `classify_points(I)` | `charge` / `discharge` / `rest` for each point |
| `assign_cycles(I, first_step)` | Cycle number for each point (0 = before the first step) |
| `cycle_summary(t, I, V, active_mass_mg)` | Per cycle: charge/discharge capacity, coulombic efficiency, specific capacity, energy, average voltages |
| `capacity_retention(capacities, reference_index)` | Retention vs a reference cycle (use 1–2 to skip formation) |
| `formation_summary(t, I, V, active_mass_mg)` | First charge/discharge capacity, first-cycle efficiency (ICE), irreversible capacity |
| `columns_from_mpr(mpr.data)` | Pull time/current/voltage out of a BioLogic `.mpr` file read with galvani |

**Conventions** (as in OperaXN): rests are ignored for capacity; capacity restarts at every charge/discharge phase; a cycle starts at the first charge (`first_step="discharge"` for anode half-cells).

```python
from galvani import BioLogic
from cellforge.cycling import columns_from_mpr, cycle_summary, formation_summary, capacity_retention

t, i, v = columns_from_mpr(BioLogic.MPRfile("CC01.mpr").data)
form = formation_summary(t, i, v, active_mass_mg=12.4)
print(form["first_discharge_capacity_mah"], form["first_cycle_efficiency"])

cycles = cycle_summary(t, i, v, active_mass_mg=12.4)
retention = capacity_retention([c["discharge_capacity_mah"] for c in cycles], reference_index=1)
```

`formation_summary(...)["first_discharge_capacity_mah"]` is what Hazbat's `formation_capacity` field records.
