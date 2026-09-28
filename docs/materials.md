# Materials library (`cellforge.materials`)

One record per material **specification**: what the material is, who supplies it, what it costs
and where each number came from. CellForge then carries those numbers through the value chain
to electrodes, cells and cost per kWh.

## Where it fits in the value chain

```
Material spec (CellForge library)   NMC811, Supplier X grade ABC: capacity, density, voltage, price, source
  └─ Material lot (Hazbat)           CAT-NMC-001: the batch received, linked to a spec
      └─ Coating (Hazbat)            loading, porosity          -> areal capacity from the spec
          └─ Cell (Hazbat)           SLP / coin / MLP           -> capacity & energy (cellforge.cell)
              └─ Test (Hazbat)       formation, cycling         -> measured capacity (cellforge.cycling)

Roll-ups: material cost per cell · cost per kWh · material intensity (kg per kWh) · supplier traceability
```

**Areal capacity is not stored on a material.** It depends on how much is coated (loading).
The library stores *specific* capacity (mAh/g), and `spec_areal_capacity()` gives the theoretical
or practical areal capacity for any loading. So one spec serves every electrode made from it.

## What each record holds

| Column | Unit / format | Notes |
|---|---|---|
| `name` | text | Required, unique, e.g. `NMC811 - Supplier X ABC` |
| `material_class` | one of: `cathode_active`, `anode_active`, `binder`, `conductive_additive`, `current_collector`, `separator`, `electrolyte`, `other` | Required |
| `formula` | text | e.g. `LiNi0.8Mn0.1Co0.1O2` |
| `supplier`, `supplier_grade` | text | Supplier and their product name/code |
| `molar_mass_g_mol`, `electrons_per_formula_unit` | g/mol, number | If both are given, theoretical capacity is **calculated** (Faraday's law) |
| `theoretical_capacity_mah_g` | mAh/g | Leave blank to calculate from the two columns above |
| `practical_capacity_mah_g` | mAh/g | Reversible capacity: supplier datasheet or your own half-cell tests |
| `first_cycle_efficiency` | fraction 0–1 | e.g. `0.90` |
| `average_voltage_v` | V | vs Li/Li⁺ for half-cell materials |
| `true_density_g_cm3`, `tap_density_g_cm3` | g/cm³ | True density feeds porosity calculations |
| `price_per_kg`, `currency`, `price_date` | number, `GBP`/`USD`/`EUR`, `YYYY-MM-DD` | Currency required with a price; currencies are never converted |
| `source_type` | `literature`, `supplier_datasheet`, `measured`, `estimate` | Where the numbers came from |
| `source_reference` | text | DOI, URL, datasheet ID or lab notebook reference |
| `notes` | text | Anything else |

Blank cells, `N/A` and `-` all mean "no data".

## Adding materials

1. Copy `cellforge/data/materials_template.csv` (headers only) and open it in Excel.
2. Add one row per material spec, from literature or supplier datasheets. Always fill `source_type` and `source_reference`.
3. Load and check it:

```python
from cellforge.materials import load_materials
lib = load_materials("our_materials.csv")          # raises with row numbers if anything is wrong
for spec in lib.values():
    print(spec.name, spec.validate())             # warnings, e.g. price without a date
```

`cellforge/data/reference_materials.csv` is a starter library of textbook values (formula, molar mass,
average voltage, true density; theoretical capacity calculated). Supplier, practical capacity,
first-cycle efficiency and prices are deliberately **blank**: fill them from real datasheets and quotes.

## Value-chain calculations

```python
from cellforge.materials import load_materials, get_material, spec_areal_capacity, active_material_mass, bill_of_materials

lib = load_materials("our_materials.csv")
nmc = get_material(lib, "NMC811 - Supplier X ABC")

q = spec_areal_capacity(nmc, loading_mg_cm2=15, active_fraction=0.96)                  # design mAh/cm²
q_max = spec_areal_capacity(nmc, 15, 0.96, basis="theoretical")                        # upper limit
m = active_material_mass(loading_mg_cm2=15, area_cm2=30, sides=10, active_fraction=0.96)  # g in an MLP

bom = bill_of_materials([(nmc, m), (get_material(lib, "PVDF - Supplier Y"), 0.09)], energy_wh=3.33)
print(bom["total_cost"], bom["currency"], bom["cost_per_kwh"], bom["unpriced"])
print(bom["rows"][0]["kg_per_kwh"])                                                     # material intensity
```

## Proposed link into Hazbat (not part of this change)

To connect the library to real batches and cells, Hazbat could store specs in the database and link
each material lot to one:

```sql
CREATE TABLE tbl_material_specs (
    spec_name                   TEXT PRIMARY KEY,
    material_class              TEXT NOT NULL,
    formula                     TEXT,
    supplier                    TEXT,
    supplier_grade              TEXT,
    molar_mass_g_mol            NUMERIC,
    electrons_per_formula_unit  NUMERIC,
    theoretical_capacity_mah_g  NUMERIC,
    practical_capacity_mah_g    NUMERIC,
    first_cycle_efficiency      NUMERIC CHECK (first_cycle_efficiency > 0 AND first_cycle_efficiency <= 1),
    average_voltage_v           NUMERIC,
    true_density_g_cm3          NUMERIC,
    tap_density_g_cm3           NUMERIC,
    source_type                 TEXT,
    source_reference            TEXT,
    notes                       TEXT
);

-- Prices change: keep a history instead of one number
CREATE TABLE tbl_material_prices (
    price_id        SERIAL PRIMARY KEY,
    spec_name       TEXT NOT NULL REFERENCES tbl_material_specs(spec_name),
    price_per_kg    NUMERIC NOT NULL CHECK (price_per_kg >= 0),
    currency        TEXT NOT NULL,
    price_date      DATE NOT NULL,
    quantity_basis  TEXT,           -- e.g. "1 kg sample", "1 t order"
    quote_reference TEXT
);

-- Each received batch points at its spec
ALTER TABLE tbl_materials ADD COLUMN spec_name TEXT REFERENCES tbl_material_specs(spec_name);
```

With that in place, a coating's areal capacity, a cell's material cost and cost per kWh can be
calculated automatically from the traceability chain, and HAZbot can answer questions such as
"which supplier's NMC gives the lowest cost per kWh in LEAP cells?".
