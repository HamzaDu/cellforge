"""
Electrode design calculations for battery manufacturing.

Covers areal capacity, N/P ratio, and related electrode-balancing formulas.
"""


def areal_capacity(specific_capacity_mah_g: float, loading_mg_cm2: float, active_material_fraction: float = 1.0) -> float:
    """
    Calculate areal capacity of an electrode coating.

    Args:
        specific_capacity_mah_g: Specific capacity of the active material (mAh/g)
        loading_mg_cm2: Coating loading, i.e. mass per unit area (mg/cm^2)
        active_material_fraction: Fraction of the coating that is active material (0-1),
            e.g. 0.95 if the composition is 95% active material, 5% binder/conductive additive

    Returns:
        Areal capacity in mAh/cm^2
    """
    if loading_mg_cm2 < 0 or specific_capacity_mah_g < 0:
        raise ValueError("Capacity and loading must be non-negative")
    if not (0 < active_material_fraction <= 1):
        raise ValueError("active_material_fraction must be between 0 and 1")

    loading_g_cm2 = loading_mg_cm2 / 1000
    return specific_capacity_mah_g * loading_g_cm2 * active_material_fraction


def np_ratio(anode_areal_capacity: float, cathode_areal_capacity: float) -> float:
    """
    Calculate the Negative-to-Positive (N/P) capacity ratio.

    Args:
        anode_areal_capacity: Areal capacity of the anode (mAh/cm^2)
        cathode_areal_capacity: Areal capacity of the cathode (mAh/cm^2)

    Returns:
        N/P ratio (dimensionless). Values > 1 mean the anode has excess capacity
        relative to the cathode, which is typical and desirable to avoid lithium plating.
    """
    if cathode_areal_capacity <= 0:
        raise ValueError("Cathode areal capacity must be positive")
    if anode_areal_capacity < 0:
        raise ValueError("Anode areal capacity must be non-negative")

    return anode_areal_capacity / cathode_areal_capacity


# ---------------------------------------------------------------------------
# Electrode physics: thickness, density and porosity
#
# Units used throughout (same as the rest of CellForge):
#   loading            mg/cm^2   (coating mass per unit area, ONE side)
#   thickness          um        (coating only, excluding the current collector)
#   density            g/cm^3
#   porosity           fraction  (0-1, e.g. 0.30 for 30 %)
#   weight fractions   fraction  (0-1, must sum to 1)
# ---------------------------------------------------------------------------

_FRACTION_SUM_TOLERANCE = 1e-3


def coating_thickness(loading_mg_cm2: float, coating_density_g_cm3: float) -> float:
    """
    Coating thickness from loading and (calendered) coating density.

    thickness (um) = loading (mg/cm^2) / density (g/cm^3) * 10

    Args:
        loading_mg_cm2: Coating loading on one side (mg/cm^2)
        coating_density_g_cm3: Coating (electrode) density, including pores (g/cm^3)

    Returns:
        Coating thickness in um (one side, excluding the current collector)
    """
    if loading_mg_cm2 < 0:
        raise ValueError("Loading must be non-negative")
    if coating_density_g_cm3 <= 0:
        raise ValueError("Coating density must be positive")
    return loading_mg_cm2 / coating_density_g_cm3 * 10


def coating_density(loading_mg_cm2: float, thickness_um: float) -> float:
    """
    Coating density from loading and measured coating thickness.

    density (g/cm^3) = loading (mg/cm^2) / thickness (um) * 10

    Args:
        loading_mg_cm2: Coating loading on one side (mg/cm^2)
        thickness_um: Coating thickness on one side, excluding the current collector (um)

    Returns:
        Coating density in g/cm^3
    """
    if loading_mg_cm2 < 0:
        raise ValueError("Loading must be non-negative")
    if thickness_um <= 0:
        raise ValueError("Thickness must be positive")
    return loading_mg_cm2 / thickness_um * 10


def formulation_true_density(components: dict) -> float:
    """
    True (skeletal, pore-free) density of an electrode formulation.

    rho_true = 1 / sum(w_i / rho_i)

    Args:
        components: Mapping of component name -> (weight_fraction, true_density_g_cm3), e.g.
            {"NMC811": (0.96, 4.75), "PVDF": (0.02, 1.78), "Carbon black": (0.02, 1.9)}
            Weight fractions are 0-1 and must add up to 1.

    Returns:
        True density of the dry coating in g/cm^3
    """
    if not components:
        raise ValueError("At least one component is required")
    total_fraction = 0.0
    specific_volume = 0.0  # cm^3 per g of coating
    for name, (fraction, density) in components.items():
        if not (0 < fraction <= 1):
            raise ValueError(f"Weight fraction for {name} must be between 0 and 1")
        if density <= 0:
            raise ValueError(f"True density for {name} must be positive")
        total_fraction += fraction
        specific_volume += fraction / density
    if abs(total_fraction - 1) > _FRACTION_SUM_TOLERANCE:
        raise ValueError(f"Weight fractions must add up to 1 (got {total_fraction:.3f})")
    return 1 / specific_volume


def porosity(coating_density_g_cm3: float, true_density_g_cm3: float) -> float:
    """
    Electrode porosity from coating density and formulation true density.

    porosity = 1 - rho_coating / rho_true

    Args:
        coating_density_g_cm3: Coating density including pores (g/cm^3),
            e.g. from coating_density()
        true_density_g_cm3: Pore-free density of the formulation (g/cm^3),
            e.g. from formulation_true_density()

    Returns:
        Porosity as a fraction (0-1)
    """
    if coating_density_g_cm3 <= 0 or true_density_g_cm3 <= 0:
        raise ValueError("Densities must be positive")
    if coating_density_g_cm3 > true_density_g_cm3:
        raise ValueError("Coating density cannot exceed the true density (porosity would be negative)")
    return 1 - coating_density_g_cm3 / true_density_g_cm3


def density_for_target_porosity(true_density_g_cm3: float, target_porosity: float) -> float:
    """
    Coating density to calender to, for a target porosity.

    rho_coating = rho_true * (1 - porosity)

    Args:
        true_density_g_cm3: Pore-free density of the formulation (g/cm^3)
        target_porosity: Desired porosity as a fraction (0-1), e.g. 0.30

    Returns:
        Target coating density in g/cm^3
    """
    if true_density_g_cm3 <= 0:
        raise ValueError("True density must be positive")
    if not (0 <= target_porosity < 1):
        raise ValueError("Target porosity must be between 0 and 1 (e.g. 0.30 for 30 %)")
    return true_density_g_cm3 * (1 - target_porosity)


def thickness_for_target_porosity(loading_mg_cm2: float, true_density_g_cm3: float, target_porosity: float) -> float:
    """
    Calendered coating thickness needed to reach a target porosity.

    Useful for setting the calender gap: combines density_for_target_porosity()
    and coating_thickness().

    Returns:
        Target coating thickness in um (one side, excluding the current collector)
    """
    target_density = density_for_target_porosity(true_density_g_cm3, target_porosity)
    return coating_thickness(loading_mg_cm2, target_density)


# ---------------------------------------------------------------------------
# N/P design helpers
# ---------------------------------------------------------------------------

# Rule-of-thumb window for graphite-based Li-ion cells. Other chemistries
# (e.g. Si-rich anodes, Li metal, Na-ion) can differ, so this is advisory only.
TYPICAL_NP_RANGE = (1.05, 1.20)


def required_loading(target_areal_capacity: float, specific_capacity_mah_g: float,
                     active_material_fraction: float = 1.0) -> float:
    """
    Coating loading needed to reach a target areal capacity (inverse of areal_capacity()).

    loading (mg/cm^2) = areal capacity (mAh/cm^2) / (specific capacity (mAh/g) * active fraction) * 1000

    Returns:
        Loading in mg/cm^2
    """
    if target_areal_capacity < 0:
        raise ValueError("Target areal capacity must be non-negative")
    if specific_capacity_mah_g <= 0:
        raise ValueError("Specific capacity must be positive")
    if not (0 < active_material_fraction <= 1):
        raise ValueError("active_material_fraction must be between 0 and 1")
    return target_areal_capacity / (specific_capacity_mah_g * active_material_fraction) * 1000


def required_anode_loading(target_np_ratio: float, cathode_areal_capacity: float,
                           anode_specific_capacity_mah_g: float, anode_active_fraction: float = 1.0) -> float:
    """
    Anode loading needed to hit a target N/P ratio against a given cathode.

    loading = N/P * Q_cathode / (q_anode * f_active) * 1000

    Args:
        target_np_ratio: Desired N/P ratio, e.g. 1.1
        cathode_areal_capacity: Cathode areal capacity (mAh/cm^2), e.g. from areal_capacity()
        anode_specific_capacity_mah_g: Anode active material specific capacity (mAh/g)
        anode_active_fraction: Fraction of the anode coating that is active material (0-1)

    Returns:
        Anode loading in mg/cm^2
    """
    if target_np_ratio <= 0:
        raise ValueError("Target N/P ratio must be positive")
    if cathode_areal_capacity <= 0:
        raise ValueError("Cathode areal capacity must be positive")
    return required_loading(target_np_ratio * cathode_areal_capacity, anode_specific_capacity_mah_g, anode_active_fraction)


def required_cathode_loading(target_np_ratio: float, anode_areal_capacity: float,
                             cathode_specific_capacity_mah_g: float, cathode_active_fraction: float = 1.0) -> float:
    """
    Cathode loading needed to hit a target N/P ratio against a given anode.

    loading = (Q_anode / N/P) / (q_cathode * f_active) * 1000

    Returns:
        Cathode loading in mg/cm^2
    """
    if target_np_ratio <= 0:
        raise ValueError("Target N/P ratio must be positive")
    if anode_areal_capacity <= 0:
        raise ValueError("Anode areal capacity must be positive")
    return required_loading(anode_areal_capacity / target_np_ratio, cathode_specific_capacity_mah_g, cathode_active_fraction)


def reversible_capacity(first_charge_capacity: float, first_cycle_efficiency: float) -> float:
    """
    Reversible capacity from first-charge capacity and first-cycle (initial coulombic) efficiency.

    Q_reversible = Q_first_charge * ICE

    Works for specific (mAh/g) or areal (mAh/cm^2) capacity; the result has the same unit.
    Use reversible capacities in np_ratio() when comparing electrodes whose
    first-cycle losses differ significantly.

    Args:
        first_charge_capacity: Capacity on the first charge (mAh/g or mAh/cm^2)
        first_cycle_efficiency: First-cycle efficiency as a fraction (0-1], e.g. 0.90

    Returns:
        Reversible capacity in the same unit as first_charge_capacity
    """
    if first_charge_capacity < 0:
        raise ValueError("Capacity must be non-negative")
    if not (0 < first_cycle_efficiency <= 1):
        raise ValueError("first_cycle_efficiency must be between 0 and 1 (e.g. 0.90 for 90 %)")
    return first_charge_capacity * first_cycle_efficiency


def area_corrected_np_ratio(anode_areal_capacity: float, cathode_areal_capacity: float,
                            anode_to_cathode_area_ratio: float) -> float:
    """
    Whole-cell N/P ratio, accounting for the anode being larger than the cathode (overhang).

    N/P_total = (Q_anode * A_anode) / (Q_cathode * A_cathode)
              = np_ratio(...) * (A_anode / A_cathode)

    Note: lithium plating risk depends on the *local* N/P (np_ratio()), because the
    overhang area sits outside the cathode. This total ratio is useful for
    capacity balancing and first-cycle lithium loss estimates.

    Args:
        anode_areal_capacity: Anode areal capacity (mAh/cm^2)
        cathode_areal_capacity: Cathode areal capacity (mAh/cm^2)
        anode_to_cathode_area_ratio: A_anode / A_cathode, e.g. 1.05
            (Hazbat's MLP "A/C area ratio" field)

    Returns:
        Area-corrected N/P ratio (dimensionless)
    """
    if anode_to_cathode_area_ratio <= 0:
        raise ValueError("Area ratio must be positive")
    return np_ratio(anode_areal_capacity, cathode_areal_capacity) * anode_to_cathode_area_ratio


def check_np_ratio(value: float, typical_range: tuple = TYPICAL_NP_RANGE) -> tuple:
    """
    Sanity-check an N/P ratio against a typical design window.

    Returns:
        (status, message) where status is "error", "warning" or "ok".
        - error:   N/P <= 0 (not physically meaningful)
        - warning: N/P < 1 (lithium plating risk) or outside the typical range
        - ok:      within the typical range
    """
    low, high = typical_range
    if value <= 0:
        return "error", f"N/P of {value:.2f} is not physically meaningful."
    if value < 1:
        return "warning", f"N/P of {value:.2f} is below 1: the anode can't hold all the lithium, so lithium plating is likely."
    if value < low:
        return "warning", f"N/P of {value:.2f} is below the typical {low:.2f}-{high:.2f} window: small safety margin against plating."
    if value > high:
        return "warning", f"N/P of {value:.2f} is above the typical {low:.2f}-{high:.2f} window: excess anode lowers energy density and increases first-cycle loss."
    return "ok", f"N/P of {value:.2f} is within the typical {low:.2f}-{high:.2f} window."
