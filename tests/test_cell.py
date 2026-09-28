import math
import pytest
from cellforge.cell import (
    rectangle_area, disc_area, box_volume, coated_sides, cell_capacity, cell_energy,
    specific_energy, energy_density, c_rate_current, c_rate, coating_mass, foil_mass,
    mass_breakdown, cell_summary, ALUMINIUM_DENSITY, COPPER_DENSITY,
)


def test_geometry():
    assert rectangle_area(50, 60) == pytest.approx(30.0)          # 5 cm x 6 cm
    assert disc_area(15) == pytest.approx(math.pi * 0.75 ** 2)    # 1.767 cm^2
    assert box_volume(60, 50, 5) == pytest.approx(15.0)           # 6 x 5 x 0.5 cm


def test_coated_sides():
    assert coated_sides(5) == 10
    assert coated_sides(4, 2) == 10
    with pytest.raises(ValueError):
        coated_sides(0)
    with pytest.raises(ValueError):
        coated_sides(-1)


def test_coin_cell_capacity():
    # 2.0 mAh/cm^2 on a 15 mm disc -> 2.0 * 1.767 = 3.534 mAh
    assert cell_capacity(2.0, disc_area(15)) == pytest.approx(2.0 * math.pi * 0.75 ** 2)


def test_mlp_capacity_cathode_and_anode_limited():
    # 3.0 mAh/cm^2, 30 cm^2 faces, 5 double-sided cathodes (10 faces) -> 900 mAh
    assert cell_capacity(3.0, 30, coated_sides(5)) == pytest.approx(900.0)
    # anode 3.3 (N/P 1.1) -> still cathode-limited; anode 2.8 (N/P < 1) -> 2.8 * 300 = 840 mAh
    assert cell_capacity(3.0, 30, 10, anode_areal_capacity=3.3) == pytest.approx(900.0)
    assert cell_capacity(3.0, 30, 10, anode_areal_capacity=2.8) == pytest.approx(840.0)


def test_energy_and_densities():
    e = cell_energy(900, 3.7)                                     # 3.33 Wh
    assert e == pytest.approx(3.33)
    assert specific_energy(e, 20) == pytest.approx(166.5)         # 3.33 Wh / 0.020 kg
    assert energy_density(e, 15) == pytest.approx(222.0)          # 3.33 Wh / 0.015 L


def test_c_rate():
    assert c_rate_current(900, 0.1) == pytest.approx(90.0)
    assert c_rate(450, 900) == pytest.approx(0.5)
    assert c_rate(-450, 900) == pytest.approx(0.5)                # discharge current sign ignored


def test_masses():
    assert coating_mass(20, 30, 2) == pytest.approx(1.2)          # 20 mg/cm^2 * 60 cm^2
    assert foil_mass(12, 30, ALUMINIUM_DENSITY) == pytest.approx(12e-4 * 30 * 2.70)
    assert foil_mass(8, 30, COPPER_DENSITY) == pytest.approx(8e-4 * 30 * 8.96)


def test_mass_breakdown():
    b = mass_breakdown({"coating": 1.0, "foil": 3.0})
    assert b["total_g"] == pytest.approx(4.0)
    assert b["components"]["coating"]["fraction"] == pytest.approx(0.25)
    with pytest.raises(ValueError):
        mass_breakdown({})
    with pytest.raises(ValueError):
        mass_breakdown({"x": -1.0})


def test_cell_summary():
    s = cell_summary(900, 3.7, mass_g=20, volume_cm3=15)
    assert s["capacity_ah"] == pytest.approx(0.9)
    assert s["energy_wh"] == pytest.approx(3.33)
    assert s["specific_energy_wh_kg"] == pytest.approx(166.5)
    assert s["energy_density_wh_l"] == pytest.approx(222.0)
    assert "specific_energy_wh_kg" not in cell_summary(900, 3.7)


def test_rejects_bad_input():
    for bad in (lambda: rectangle_area(0, 10), lambda: disc_area(-1), lambda: cell_capacity(0, 30),
                lambda: cell_capacity(3, 30, 0), lambda: cell_energy(900, 0), lambda: specific_energy(3, 0),
                lambda: foil_mass(0, 30), lambda: coating_mass(-1, 30)):
        with pytest.raises(ValueError):
            bad()
