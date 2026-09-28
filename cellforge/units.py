"""
Unit conversions for battery design and testing.

CellForge functions take numbers in fixed units (see docs/units.md) and put the
unit in the argument name, e.g. `loading_mg_cm2`. Use this module to convert
supplier or literature values into those units first:

    convert(2.5, "g/m2", "mg/cm2")      -> 0.25
    convert(3.2, "Ah", "mAh")           -> 3200
    percent_to_fraction(96)             -> 0.96

Unit spellings are forgiving: "µm"/"um", "cm²"/"cm2"/"cm^2", "g/cm³"/"g/cc" all work.
"""

# Each unit: (quantity, factor to that quantity's base unit)
_UNITS = {
    # mass (base g)
    "ug": ("mass", 1e-6), "mg": ("mass", 1e-3), "g": ("mass", 1.0), "kg": ("mass", 1e3), "t": ("mass", 1e6),
    # length (base m)
    "nm": ("length", 1e-9), "um": ("length", 1e-6), "mm": ("length", 1e-3), "cm": ("length", 1e-2), "m": ("length", 1.0),
    # area (base m2)
    "mm2": ("area", 1e-6), "cm2": ("area", 1e-4), "m2": ("area", 1.0),
    # volume (base L)
    "ul": ("volume", 1e-6), "ml": ("volume", 1e-3), "cm3": ("volume", 1e-3), "l": ("volume", 1.0), "m3": ("volume", 1e3),
    # charge / capacity (base mAh)
    "uah": ("charge", 1e-3), "mah": ("charge", 1.0), "ah": ("charge", 1e3), "c": ("charge", 1 / 3.6),
    # energy (base Wh)
    "mwh": ("energy", 1e-3), "wh": ("energy", 1.0), "kwh": ("energy", 1e3), "j": ("energy", 1 / 3600),
    # current (base mA)
    "ua": ("current", 1e-3), "ma": ("current", 1.0), "a": ("current", 1e3),
    # time (base s)
    "s": ("time", 1.0), "min": ("time", 60.0), "h": ("time", 3600.0),
    # density (base g/cm3)
    "g/cm3": ("density", 1.0), "g/ml": ("density", 1.0), "kg/m3": ("density", 1e-3), "kg/l": ("density", 1.0),
    # areal loading (base mg/cm2)
    "mg/cm2": ("loading", 1.0), "g/m2": ("loading", 0.1), "g/cm2": ("loading", 1e3),
    # specific capacity (base mAh/g)
    "mah/g": ("specific_capacity", 1.0), "ah/kg": ("specific_capacity", 1.0), "ah/g": ("specific_capacity", 1e3),
    # areal capacity (base mAh/cm2)
    "mah/cm2": ("areal_capacity", 1.0), "ah/m2": ("areal_capacity", 0.1), "uah/cm2": ("areal_capacity", 1e-3),
    # specific energy (base Wh/kg)
    "wh/kg": ("specific_energy", 1.0), "mwh/g": ("specific_energy", 1.0), "kwh/kg": ("specific_energy", 1e3),
    # energy density (base Wh/L)
    "wh/l": ("energy_density", 1.0), "mwh/cm3": ("energy_density", 1.0), "kwh/m3": ("energy_density", 1.0),
    # price per mass (base per kg; currency is not converted)
    "per_kg": ("price_per_mass", 1.0), "per_g": ("price_per_mass", 1e3), "per_t": ("price_per_mass", 1e-3),
}

_ALIASES = {"µ": "u", "μ": "u", "²": "2", "³": "3", "^": "", " ": "", "g/cc": "g/cm3", "/tonne": "/t", "per_tonne": "per_t"}


def normalise_unit(unit: str) -> str:
    """Tidy a unit string: 'µm' -> 'um', 'cm²' -> 'cm2', 'mAh/cm^2' -> 'mah/cm2'."""
    u = str(unit).strip()
    for old, new in _ALIASES.items():
        u = u.replace(old, new)
    u = u.lower()
    if u not in _UNITS:
        raise ValueError(f"Unknown unit '{unit}'. Known units: {', '.join(sorted(_UNITS))}")
    return u


def quantity_of(unit: str) -> str:
    """What a unit measures, e.g. 'mg/cm2' -> 'loading'."""
    return _UNITS[normalise_unit(unit)][0]


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """
    Convert a value between two units of the same quantity.

    Raises ValueError for unknown units or mismatched quantities
    (e.g. converting mAh to Wh needs a voltage, so it isn't allowed here).
    """
    f, t = normalise_unit(from_unit), normalise_unit(to_unit)
    (fq, ff), (tq, tf) = _UNITS[f], _UNITS[t]
    if fq != tq:
        raise ValueError(f"Can't convert {from_unit} ({fq}) to {to_unit} ({tq})")
    return value * ff / tf


def percent_to_fraction(percent: float) -> float:
    """96 (%) -> 0.96. CellForge uses fractions (0-1) for porosity, weight fractions and efficiencies."""
    if not (0 <= percent <= 100):
        raise ValueError("Percent must be between 0 and 100")
    return percent / 100


def fraction_to_percent(fraction: float) -> float:
    """0.96 -> 96 (%)."""
    if not (0 <= fraction <= 1):
        raise ValueError("Fraction must be between 0 and 1")
    return fraction * 100


def celsius_to_kelvin(celsius: float) -> float:
    """25 degC -> 298.15 K."""
    kelvin = celsius + 273.15
    if kelvin < 0:
        raise ValueError("Temperature below absolute zero")
    return kelvin


def kelvin_to_celsius(kelvin: float) -> float:
    """298.15 K -> 25 degC."""
    if kelvin < 0:
        raise ValueError("Temperature below absolute zero")
    return kelvin - 273.15


def charge_to_energy(capacity_mah: float, voltage_v: float) -> float:
    """Capacity (mAh) at an average voltage (V) -> energy (Wh)."""
    return capacity_mah * voltage_v / 1000


def energy_to_charge(energy_wh: float, voltage_v: float) -> float:
    """Energy (Wh) at an average voltage (V) -> capacity (mAh)."""
    if voltage_v <= 0:
        raise ValueError("Voltage must be positive")
    return energy_wh / voltage_v * 1000
