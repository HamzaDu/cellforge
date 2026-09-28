import pytest
from cellforge.units import (
    convert, normalise_unit, quantity_of, percent_to_fraction, fraction_to_percent,
    celsius_to_kelvin, kelvin_to_celsius, charge_to_energy, energy_to_charge,
)


@pytest.mark.parametrize("value, frm, to, expected", [
    (1500, "mg", "g", 1.5),
    (12, "µm", "mm", 0.012),
    (1, "cm²", "mm2", 100),
    (25, "g/m2", "mg/cm2", 2.5),            # supplier loading in g/m2
    (3.2, "Ah", "mAh", 3200),
    (1, "mAh", "C", 3.6),                   # coulombs
    (1, "Wh", "J", 3600),
    (2.26, "g/cc", "kg/m3", 2260),
    (3, "mAh/cm^2", "Ah/m2", 30),
    (200, "mAh/g", "Ah/kg", 200),
    (0.25, "kWh/kg", "Wh/kg", 250),
    (18, "per_kg", "per_t", 18000),         # price per kg -> per tonne
    (90, "min", "h", 1.5),
])
def test_convert(value, frm, to, expected):
    assert convert(value, frm, to) == pytest.approx(expected)


def test_normalise_unit():
    assert normalise_unit(" µm ") == "um"
    assert normalise_unit("mAh/cm²") == "mah/cm2"
    assert quantity_of("g/m2") == "loading"


def test_convert_rejects_unknown_and_mismatched_units():
    with pytest.raises(ValueError):
        convert(1, "furlong", "m")
    with pytest.raises(ValueError):
        convert(1, "mAh", "Wh")  # needs a voltage -> use charge_to_energy
    with pytest.raises(ValueError):
        convert(1, "mg", "mm")


def test_percent_fraction():
    assert percent_to_fraction(96) == pytest.approx(0.96)
    assert fraction_to_percent(0.3) == pytest.approx(30)
    with pytest.raises(ValueError):
        percent_to_fraction(120)
    with pytest.raises(ValueError):
        fraction_to_percent(30)  # 30 is a percent, not a fraction


def test_temperature():
    assert celsius_to_kelvin(25) == pytest.approx(298.15)
    assert kelvin_to_celsius(298.15) == pytest.approx(25)
    with pytest.raises(ValueError):
        celsius_to_kelvin(-300)


def test_charge_energy():
    assert charge_to_energy(900, 3.7) == pytest.approx(3.33)
    assert energy_to_charge(3.33, 3.7) == pytest.approx(900)
    with pytest.raises(ValueError):
        energy_to_charge(3.33, 0)
