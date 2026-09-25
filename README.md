# cellforge

Battery manufacturing calculations toolkit electrode design, capacity, and energy density formulas

## Electrode module (`cellforge.electrode`)

Units: loading mg/cm² (one side) · thickness µm (coating only) · density g/cm³ · porosity and fractions 0–1 · capacity mAh/g or mAh/cm².

| Function | What it gives you |
|---|---|
| `areal_capacity(q, loading, f_active)` | Areal capacity (mAh/cm²) |
| `np_ratio(Q_anode, Q_cathode)` | N/P ratio (local) |
| `coating_thickness(loading, density)` | Coating thickness (µm) |
| `coating_density(loading, thickness)` | Coating density (g/cm³) |
| `formulation_true_density({name: (w, rho)})` | Pore-free density of a formulation (g/cm³) |
| `porosity(coating_density, true_density)` | Porosity (0–1) |
| `density_for_target_porosity(true_density, p)` | Calender density for a target porosity |
| `thickness_for_target_porosity(loading, true_density, p)` | Calendered thickness for a target porosity (µm) |
| `required_loading(Q_target, q, f_active)` | Loading for a target areal capacity (mg/cm²) |
| `required_anode_loading(np, Q_cathode, q_anode, f_active)` | Anode loading for a target N/P |
| `required_cathode_loading(np, Q_anode, q_cathode, f_active)` | Cathode loading for a target N/P |
| `reversible_capacity(Q_first_charge, ICE)` | Reversible capacity after first-cycle loss |
| `area_corrected_np_ratio(Q_a, Q_c, A_a/A_c)` | Whole-cell N/P including anode overhang |
| `check_np_ratio(np)` | `("ok" / "warning" / "error", message)` against a typical 1.05–1.20 window |

```python
from cellforge.electrode import *

rho_true = formulation_true_density({"NMC811": (0.96, 4.75), "PVDF": (0.02, 1.78), "CB": (0.02, 1.9)})
gap_um   = thickness_for_target_porosity(18, rho_true, 0.30)           # calender to this coating thickness
q_cat    = areal_capacity(200, 18, 0.96)                                # mAh/cm²
anode_ld = required_anode_loading(1.1, q_cat, 350, 0.95)               # mg/cm² for N/P = 1.1
print(check_np_ratio(np_ratio(areal_capacity(350, anode_ld, 0.95), q_cat)))
```

Material densities and capacities in the examples are illustrative; use your own measured values.
