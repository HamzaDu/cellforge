"""
Cell-level capacity, energy and mass: from electrode design to Ah, Wh, Wh/kg and Wh/L.

Covers coin cells, single-layer pouch (SLP) and multi-layer pouch (MLP) stacks.
Plain Python, no extra dependencies.

Units:
    lengths        mm   (electrode and cell dimensions)
    thickness      um   (foils, coatings)
    area           cm^2
    areal capacity mAh/cm^2
    capacity       mAh
    energy         Wh
    mass           g
    volume         cm^3 (= mL)
"""

from math import pi

# Standard handbook densities of current-collector foils (g/cm^3)
ALUMINIUM_DENSITY = 2.70
COPPER_DENSITY = 8.96


def _positive(name, value):
    if value <= 0:
        raise ValueError(f"{name} must be positive")


# --- Geometry -------------------------------------------------------------------

def rectangle_area(width_mm: float, length_mm: float) -> float:
    """Area of a rectangular electrode in cm^2 (e.g. pouch cell cathode)."""
    _positive("Width", width_mm)
    _positive("Length", length_mm)
    return width_mm * length_mm / 100


def disc_area(diameter_mm: float) -> float:
    """Area of a punched disc electrode in cm^2 (e.g. 15 mm coin cell cathode -> 1.767 cm^2)."""
    _positive("Diameter", diameter_mm)
    return pi * (diameter_mm / 2) ** 2 / 100


def box_volume(length_mm: float, width_mm: float, thickness_mm: float) -> float:
    """Volume of a rectangular cell body in cm^3 (mL), e.g. a pouch cell without tabs."""
    for name, v in (("Length", length_mm), ("Width", width_mm), ("Thickness", thickness_mm)):
        _positive(name, v)
    return length_mm * width_mm * thickness_mm / 1000


def coated_sides(double_sided_layers: int, single_sided_layers: int = 0) -> int:
    """
    Number of coated faces in a stack, e.g. an MLP with 5 double-sided cathodes -> 10.

    Pass the cathode layer counts when working out cell capacity.
    """
    if double_sided_layers < 0 or single_sided_layers < 0:
        raise ValueError("Layer counts must be non-negative")
    sides = 2 * double_sided_layers + single_sided_layers
    if sides == 0:
        raise ValueError("At least one coated side is needed")
    return sides


# --- Capacity & energy ------------------------------------------------------------

def cell_capacity(cathode_areal_capacity: float, cathode_area_cm2: float, sides: int = 1,
                  anode_areal_capacity: float = None) -> float:
    """
    Design capacity of a cell (mAh).

    Q = Q_areal (mAh/cm^2) * A_cathode (cm^2) * number of coated cathode sides

    If the anode areal capacity is given, each face is limited by the smaller of the
    two (i.e. N/P < 1 makes the cell anode-limited). Assumes the anode is at least as
    large as the cathode, as in normal designs.

    Args:
        cathode_areal_capacity: mAh/cm^2 (e.g. from cellforge.electrode.areal_capacity)
        cathode_area_cm2: Area of ONE cathode face (rectangle_area / disc_area)
        sides: Number of coated cathode faces (coated_sides(); 1 for coin cells / SLP)
        anode_areal_capacity: Optional, mAh/cm^2

    Returns:
        Capacity in mAh (divide by 1000 for Ah)
    """
    _positive("Cathode areal capacity", cathode_areal_capacity)
    _positive("Cathode area", cathode_area_cm2)
    if sides < 1:
        raise ValueError("sides must be at least 1")
    per_area = cathode_areal_capacity
    if anode_areal_capacity is not None:
        _positive("Anode areal capacity", anode_areal_capacity)
        per_area = min(cathode_areal_capacity, anode_areal_capacity)
    return per_area * cathode_area_cm2 * sides


def cell_energy(capacity_mah: float, average_voltage_v: float) -> float:
    """Energy in Wh = capacity (mAh) * average discharge voltage (V) / 1000."""
    _positive("Capacity", capacity_mah)
    _positive("Average voltage", average_voltage_v)
    return capacity_mah * average_voltage_v / 1000


def specific_energy(energy_wh: float, mass_g: float) -> float:
    """Gravimetric energy density in Wh/kg."""
    _positive("Energy", energy_wh)
    _positive("Mass", mass_g)
    return energy_wh / (mass_g / 1000)


def energy_density(energy_wh: float, volume_cm3: float) -> float:
    """Volumetric energy density in Wh/L."""
    _positive("Energy", energy_wh)
    _positive("Volume", volume_cm3)
    return energy_wh / (volume_cm3 / 1000)


def c_rate_current(capacity_mah: float, c_rate: float) -> float:
    """Current (mA) for a given C-rate, e.g. C/10 on a 900 mAh cell -> 90 mA."""
    _positive("Capacity", capacity_mah)
    _positive("C-rate", c_rate)
    return capacity_mah * c_rate


def c_rate(current_ma: float, capacity_mah: float) -> float:
    """C-rate for a given current, e.g. 450 mA on a 900 mAh cell -> 0.5 (C/2)."""
    _positive("Capacity", capacity_mah)
    return abs(current_ma) / capacity_mah


# --- Mass ------------------------------------------------------------------------

def coating_mass(loading_mg_cm2: float, area_cm2: float, sides: int = 1) -> float:
    """Dry coating mass in g = loading (mg/cm^2) * area (cm^2) * sides / 1000."""
    if loading_mg_cm2 < 0:
        raise ValueError("Loading must be non-negative")
    _positive("Area", area_cm2)
    if sides < 1:
        raise ValueError("sides must be at least 1")
    return loading_mg_cm2 * area_cm2 * sides / 1000


def foil_mass(thickness_um: float, area_cm2: float, density_g_cm3: float = ALUMINIUM_DENSITY) -> float:
    """Current-collector foil mass in g (use COPPER_DENSITY for anode foils)."""
    _positive("Thickness", thickness_um)
    _positive("Area", area_cm2)
    _positive("Density", density_g_cm3)
    return thickness_um * 1e-4 * area_cm2 * density_g_cm3


def mass_breakdown(components: dict) -> dict:
    """
    Total mass and share of each component.

    Args:
        components: {name: mass_g}, e.g. {"Cathode coating": 1.2, "Al foil": 0.1, ...}

    Returns:
        {"total_g": ..., "components": {name: {"mass_g": ..., "fraction": ...}}}
    """
    if not components:
        raise ValueError("At least one component is required")
    for name, m in components.items():
        if m < 0:
            raise ValueError(f"Mass for {name} must be non-negative")
    total = sum(components.values())
    _positive("Total mass", total)
    return {"total_g": total,
            "components": {n: {"mass_g": m, "fraction": m / total} for n, m in components.items()}}


def cell_summary(capacity_mah: float, average_voltage_v: float, mass_g: float = None, volume_cm3: float = None) -> dict:
    """
    Headline numbers in one call: capacity (mAh, Ah), energy (Wh) and, if given,
    specific energy (Wh/kg) and energy density (Wh/L).
    """
    energy = cell_energy(capacity_mah, average_voltage_v)
    out = {"capacity_mah": capacity_mah, "capacity_ah": capacity_mah / 1000, "energy_wh": energy}
    if mass_g is not None:
        out["specific_energy_wh_kg"] = specific_energy(energy, mass_g)
    if volume_cm3 is not None:
        out["energy_density_wh_l"] = energy_density(energy, volume_cm3)
    return out
