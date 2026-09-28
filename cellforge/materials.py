"""
Materials library: one record per material *specification* (what a material is, who
supplies it, what it costs and where the numbers came from), plus value-chain
calculations that carry those numbers through to electrodes and cells.

How it fits the value chain
---------------------------
    Material spec (this module)      NMC811 from supplier X: capacity, density, price, source
      -> Material lot (Hazbat)       CAT-NMC-001: the batch received, linked to a spec
        -> Coating (Hazbat)          loading, porosity   -> areal capacity from the spec
          -> Cell (Hazbat)           SLP / coin / MLP    -> capacity, energy (cellforge.cell)
            -> Test (Hazbat)         formation, cycling  -> practical capacity (cellforge.cycling)
    Roll-ups: material cost per cell, cost per kWh, material intensity (kg/kWh), supplier traceability.

Areal capacity is NOT stored on a material: it depends on the coating loading.
The spec stores specific capacity (mAh/g); `spec_areal_capacity()` turns that into
theoretical or practical areal capacity for any loading.

Units follow docs/units.md: mAh/g, g/cm3, V, fractions 0-1, price per kg.
"""

import csv
from dataclasses import dataclass, fields, asdict
from pathlib import Path
from typing import Optional

FARADAY_MAH_PER_MOL = 96485.33212 / 3.6  # 26801.48 mAh/mol

MATERIAL_CLASSES = ("cathode_active", "anode_active", "binder", "conductive_additive",
                    "current_collector", "separator", "electrolyte", "other")
SOURCE_TYPES = ("literature", "supplier_datasheet", "measured", "estimate")
BLANK_MARKERS = {"", "n/a", "na", "-", "—", "none", "null"}

DATA_DIR = Path(__file__).parent / "data"
REFERENCE_LIBRARY = DATA_DIR / "reference_materials.csv"
BLANK_TEMPLATE = DATA_DIR / "materials_template.csv"


def theoretical_specific_capacity(molar_mass_g_mol: float, electrons_per_formula_unit: float) -> float:
    """
    Theoretical specific capacity from Faraday's law: q = n * F / (3.6 * M), in mAh/g.

    e.g. LiFePO4 (M = 157.76 g/mol, n = 1) -> 169.9 mAh/g
    """
    if molar_mass_g_mol <= 0:
        raise ValueError("Molar mass must be positive")
    if electrons_per_formula_unit <= 0:
        raise ValueError("Electrons per formula unit must be positive")
    return electrons_per_formula_unit * FARADAY_MAH_PER_MOL / molar_mass_g_mol


@dataclass
class MaterialSpec:
    """One material specification. Only `name` and `material_class` are required."""
    name: str
    material_class: str
    formula: Optional[str] = None
    supplier: Optional[str] = None
    supplier_grade: Optional[str] = None            # supplier's product name / code
    molar_mass_g_mol: Optional[float] = None
    electrons_per_formula_unit: Optional[float] = None
    theoretical_capacity_mah_g: Optional[float] = None  # filled from molar mass if blank
    practical_capacity_mah_g: Optional[float] = None    # reversible, from datasheet or own tests
    first_cycle_efficiency: Optional[float] = None       # fraction 0-1
    average_voltage_v: Optional[float] = None             # vs Li/Li+ for half-cell materials
    true_density_g_cm3: Optional[float] = None
    tap_density_g_cm3: Optional[float] = None
    price_per_kg: Optional[float] = None
    currency: Optional[str] = None                       # e.g. GBP, USD, EUR
    price_date: Optional[str] = None                     # YYYY-MM-DD the price was quoted
    source_type: Optional[str] = None                    # literature / supplier_datasheet / measured / estimate
    source_reference: Optional[str] = None               # DOI, URL, datasheet ID, lab notebook ref
    notes: Optional[str] = None

    def __post_init__(self):
        if self.theoretical_capacity_mah_g is None and self.molar_mass_g_mol and self.electrons_per_formula_unit:
            self.theoretical_capacity_mah_g = theoretical_specific_capacity(
                self.molar_mass_g_mol, self.electrons_per_formula_unit)

    @property
    def is_active(self) -> bool:
        return self.material_class in ("cathode_active", "anode_active")

    def capacity(self, basis: str = "practical") -> float:
        """Specific capacity (mAh/g) on a 'practical' or 'theoretical' basis."""
        if basis not in ("practical", "theoretical"):
            raise ValueError("basis must be 'practical' or 'theoretical'")
        value = self.practical_capacity_mah_g if basis == "practical" else self.theoretical_capacity_mah_g
        if value is None:
            raise ValueError(f"{self.name} has no {basis} capacity recorded")
        return value

    def validate(self) -> list:
        """
        Check the record. Returns a list of (level, message); level is 'error' or 'warning'.
        An empty list means the record is fine.
        """
        issues = []
        def err(m): issues.append(("error", m))
        def warn(m): issues.append(("warning", m))

        if not self.name or not str(self.name).strip():
            err("Name is required.")
        if self.material_class not in MATERIAL_CLASSES:
            err(f"material_class must be one of {', '.join(MATERIAL_CLASSES)}.")
        for field_name in ("molar_mass_g_mol", "electrons_per_formula_unit", "theoretical_capacity_mah_g",
                           "practical_capacity_mah_g", "average_voltage_v", "true_density_g_cm3",
                           "tap_density_g_cm3", "price_per_kg"):
            v = getattr(self, field_name)
            if v is not None and v < 0:
                err(f"{field_name} must not be negative.")
        if self.first_cycle_efficiency is not None and not (0 < self.first_cycle_efficiency <= 1):
            err("first_cycle_efficiency must be a fraction between 0 and 1 (e.g. 0.90, not 90).")
        if self.source_type is not None and self.source_type not in SOURCE_TYPES:
            err(f"source_type must be one of {', '.join(SOURCE_TYPES)}.")
        if self.price_per_kg is not None and not self.currency:
            err("A price needs a currency (e.g. GBP).")
        if self.price_per_kg is not None and not self.price_date:
            warn("Price has no date; prices change, so record when it was quoted.")
        if (self.practical_capacity_mah_g and self.theoretical_capacity_mah_g
                and self.practical_capacity_mah_g > self.theoretical_capacity_mah_g * 1.02):
            warn("Practical capacity is higher than theoretical; check the values.")
        if (self.tap_density_g_cm3 and self.true_density_g_cm3
                and self.tap_density_g_cm3 > self.true_density_g_cm3):
            err("Tap density can't exceed true density.")
        if self.is_active and self.theoretical_capacity_mah_g is None and self.practical_capacity_mah_g is None:
            warn("Active material has no capacity recorded.")
        if not self.source_reference:
            warn("No source reference (DOI, datasheet or notebook); add one so values can be traced.")
        return issues


# --- Reading and writing the library (CSV, editable in Excel) ----------------------

_NUMERIC = {f.name for f in fields(MaterialSpec)} - {
    "name", "material_class", "formula", "supplier", "supplier_grade", "currency",
    "price_date", "source_type", "source_reference", "notes"}
COLUMNS = [f.name for f in fields(MaterialSpec)]


def _clean(value, numeric: bool, column: str, row_num: int):
    if value is None or str(value).strip().lower() in BLANK_MARKERS:
        return None
    value = str(value).strip()
    if not numeric:
        return value
    try:
        return float(value)
    except ValueError:
        raise ValueError(f"Row {row_num}: '{value}' in column {column} is not a number")


def load_materials(path=None, strict: bool = True) -> dict:
    """
    Load a materials library CSV into {name: MaterialSpec}.

    Blank cells, N/A and - mean "no data". With strict=True (default) any record
    with an 'error' from validate() raises ValueError listing every problem.
    Defaults to the bundled reference library.
    """
    path = Path(path) if path else REFERENCE_LIBRARY
    library, problems = {}, []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        unknown = [c for c in (reader.fieldnames or []) if c and c.strip() not in COLUMNS]
        if unknown:
            raise ValueError(f"Unknown columns: {', '.join(unknown)}. Expected: {', '.join(COLUMNS)}")
        for row_num, row in enumerate(reader, start=2):
            if not any((v or "").strip() for v in row.values()):
                continue  # skip blank lines
            data = {c.strip(): _clean(v, c.strip() in _NUMERIC, c.strip(), row_num) for c, v in row.items() if c}
            spec = MaterialSpec(**data)
            if spec.name in library:
                problems.append(f"Row {row_num}: duplicate name '{spec.name}'")
            for level, msg in spec.validate():
                if level == "error":
                    problems.append(f"Row {row_num} ({spec.name}): {msg}")
            library[spec.name] = spec
    if strict and problems:
        raise ValueError("Materials library has problems:\n" + "\n".join(problems))
    return library


def save_materials(library: dict, path) -> None:
    """Write {name: MaterialSpec} to CSV (blank cells for missing values)."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        for spec in library.values():
            writer.writerow({k: ("" if v is None else v) for k, v in asdict(spec).items()})


def get_material(library: dict, name: str) -> MaterialSpec:
    """Look up a material by name (case-insensitive)."""
    for key, spec in library.items():
        if key.lower() == name.strip().lower():
            return spec
    raise KeyError(f"'{name}' is not in the library. Available: {', '.join(sorted(library))}")


# --- Value-chain calculations ---------------------------------------------------------

def spec_areal_capacity(spec: MaterialSpec, loading_mg_cm2: float, active_fraction: float = 1.0,
                        basis: str = "practical") -> float:
    """
    Areal capacity (mAh/cm^2) of a coating made from this material at a given loading.

    Use basis='theoretical' for the upper limit, 'practical' for the design value.
    """
    if loading_mg_cm2 < 0:
        raise ValueError("Loading must be non-negative")
    if not (0 < active_fraction <= 1):
        raise ValueError("active_fraction must be between 0 and 1")
    return spec.capacity(basis) * loading_mg_cm2 / 1000 * active_fraction


def active_material_mass(loading_mg_cm2: float, area_cm2: float, sides: int = 1, active_fraction: float = 1.0) -> float:
    """Mass (g) of active material in an electrode: loading * area * sides * active fraction / 1000."""
    if loading_mg_cm2 < 0 or area_cm2 <= 0 or sides < 1:
        raise ValueError("Loading must be >= 0, area > 0 and sides >= 1")
    if not (0 < active_fraction <= 1):
        raise ValueError("active_fraction must be between 0 and 1")
    return loading_mg_cm2 * area_cm2 * sides * active_fraction / 1000


def material_cost(spec: MaterialSpec, mass_g: float) -> float:
    """Cost of `mass_g` grams of this material, in the spec's currency."""
    if mass_g < 0:
        raise ValueError("Mass must be non-negative")
    if spec.price_per_kg is None or not spec.currency:
        raise ValueError(f"{spec.name} has no price and currency recorded")
    return spec.price_per_kg * mass_g / 1000


def bill_of_materials(items: list, energy_wh: float = None) -> dict:
    """
    Cost and mass roll-up for a cell.

    Args:
        items: list of (MaterialSpec, mass_g) pairs, e.g. from active_material_mass()
        energy_wh: optional cell energy (Wh) to add cost per kWh and material intensity

    Returns:
        {"rows": [{material, supplier, mass_g, cost, cost_share, kg_per_kwh?}],
         "total_mass_g", "total_cost", "currency", "cost_per_kwh"?, "unpriced": [...]}
        Materials without a price are listed in "unpriced" and left out of the cost.
        All priced materials must share one currency.
    """
    if not items:
        raise ValueError("No materials given")
    if energy_wh is not None and energy_wh <= 0:
        raise ValueError("Energy must be positive")
    currencies = {s.currency for s, _ in items if s.price_per_kg is not None}
    if len(currencies) > 1:
        raise ValueError(f"Mixed currencies ({', '.join(sorted(currencies))}); convert prices to one currency first")
    currency = currencies.pop() if currencies else None

    rows, total_cost, unpriced = [], 0.0, []
    for spec, mass in items:
        cost = material_cost(spec, mass) if spec.price_per_kg is not None else None
        if cost is None:
            unpriced.append(spec.name)
        else:
            total_cost += cost
        row = {"material": spec.name, "supplier": spec.supplier, "mass_g": mass, "cost": cost}
        if energy_wh is not None:
            row["kg_per_kwh"] = (mass / 1000) / (energy_wh / 1000)  # material intensity
        rows.append(row)
    for row in rows:
        row["cost_share"] = (row["cost"] / total_cost) if row["cost"] is not None and total_cost > 0 else None

    out = {"rows": rows, "total_mass_g": sum(m for _, m in items),
           "total_cost": total_cost if currency else None, "currency": currency, "unpriced": unpriced}
    if energy_wh is not None and currency:
        out["cost_per_kwh"] = total_cost / (energy_wh / 1000)
    return out
