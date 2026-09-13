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
