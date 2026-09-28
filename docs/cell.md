# Cell capacity & energy (`cellforge.cell`)

From electrode design to Ah, Wh, Wh/kg and Wh/L for coin cells, SLP and MLP stacks. Plain Python, no extra dependencies.

**Units:** dimensions mm · foil/coating thickness µm · area cm² · areal capacity mAh/cm² · capacity mAh · energy Wh · mass g · volume cm³ (mL).

| Function | What it gives you |
|---|---|
| `rectangle_area(w, l)` / `disc_area(d)` | Electrode face area (cm²) |
| `coated_sides(double, single)` | Number of coated cathode faces in a stack |
| `cell_capacity(Q_cat, A_cat, sides, Q_anode)` | Design capacity (mAh); anode-limited if N/P < 1 |
| `cell_energy(Q, V_avg)` | Energy (Wh) |
| `specific_energy(Wh, g)` / `energy_density(Wh, cm³)` | Wh/kg and Wh/L |
| `box_volume(l, w, t)` | Cell body volume (cm³) |
| `c_rate_current(Q, C)` / `c_rate(I, Q)` | Current for a C-rate, and C-rate for a current |
| `coating_mass(loading, A, sides)` / `foil_mass(t, A, rho)` | Component masses (g); `ALUMINIUM_DENSITY`, `COPPER_DENSITY` |
| `mass_breakdown({name: g})` | Total mass and each component's share |
| `cell_summary(Q, V_avg, mass_g, volume_cm3)` | Capacity, energy, Wh/kg, Wh/L in one call |

```python
from cellforge.electrode import areal_capacity
from cellforge.cell import *

q_cat = areal_capacity(200, 15, 0.96)                    # mAh/cm²
area  = rectangle_area(50, 60)                           # 30 cm² per face
cap   = cell_capacity(q_cat, area, coated_sides(5))      # MLP, 5 double-sided cathodes
print(c_rate_current(cap, 0.1), "mA for C/10 formation")
print(cell_summary(cap, 3.7, mass_g=24.0, volume_cm3=15.0))
```

The average discharge voltage can come from `cellforge.cycling.cycle_summary(...)["average_discharge_voltage_v"]`.
