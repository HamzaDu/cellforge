import pytest
from cellforge.electrode import (
    areal_capacity, np_ratio,
    coating_thickness, coating_density, formulation_true_density, porosity,
    density_for_target_porosity, thickness_for_target_porosity,
    required_loading, required_anode_loading, required_cathode_loading,
    reversible_capacity, area_corrected_np_ratio, check_np_ratio,
)


# --- Electrode physics -------------------------------------------------------

def test_coating_thickness_basic():
    # 10 mg/cm^2 at 2.5 g/cm^3 -> 0.010 g/cm^2 / 2.5 g/cm^3 = 0.004 cm = 40 um
    assert coating_thickness(10, 2.5) == pytest.approx(40.0)


def test_coating_density_is_inverse_of_thickness():
    # 10 mg/cm^2 over 40 um -> 2.5 g/cm^3
    assert coating_density(10, 40) == pytest.approx(2.5)
    assert coating_density(12.3, coating_thickness(12.3, 3.1)) == pytest.approx(3.1)


def test_coating_thickness_and_density_reject_bad_input():
    with pytest.raises(ValueError):
        coating_thickness(-1, 2.5)
    with pytest.raises(ValueError):
        coating_thickness(10, 0)
    with pytest.raises(ValueError):
        coating_density(10, 0)


def test_formulation_true_density_two_components():
    # 50 wt% at 2.0 and 50 wt% at 4.0 -> 1 / (0.25 + 0.125) = 2.6667 g/cm^3
    assert formulation_true_density({"A": (0.5, 2.0), "B": (0.5, 4.0)}) == pytest.approx(8 / 3)


def test_formulation_true_density_typical_cathode():
    # 96/2/2 NMC811 / PVDF / carbon black (illustrative densities)
    expected = 1 / (0.96 / 4.75 + 0.02 / 1.78 + 0.02 / 1.9)
    comps = {"NMC811": (0.96, 4.75), "PVDF": (0.02, 1.78), "CB": (0.02, 1.9)}
    assert formulation_true_density(comps) == pytest.approx(expected)


def test_formulation_true_density_rejects_bad_fractions():
    with pytest.raises(ValueError):
        formulation_true_density({"A": (0.5, 2.0), "B": (0.4, 4.0)})  # sums to 0.9
    with pytest.raises(ValueError):
        formulation_true_density({"A": (0, 2.0), "B": (1.0, 4.0)})    # zero fraction
    with pytest.raises(ValueError):
        formulation_true_density({"A": (1.0, 0)})                     # zero density
    with pytest.raises(ValueError):
        formulation_true_density({})


def test_porosity_basic():
    # 3.0 g/cm^3 coating from a 4.0 g/cm^3 formulation -> 25 % porosity
    assert porosity(3.0, 4.0) == pytest.approx(0.25)


def test_porosity_rejects_impossible_density():
    with pytest.raises(ValueError):
        porosity(4.5, 4.0)  # denser than pore-free material
    with pytest.raises(ValueError):
        porosity(0, 4.0)


def test_density_and_thickness_for_target_porosity():
    # 25 % porosity from 4.0 g/cm^3 -> 3.0 g/cm^3; 15 mg/cm^2 at 3.0 g/cm^3 -> 50 um
    assert density_for_target_porosity(4.0, 0.25) == pytest.approx(3.0)
    assert thickness_for_target_porosity(15, 4.0, 0.25) == pytest.approx(50.0)


def test_target_porosity_round_trip():
    true_rho = formulation_true_density({"NMC811": (0.96, 4.75), "PVDF": (0.02, 1.78), "CB": (0.02, 1.9)})
    t = thickness_for_target_porosity(18, true_rho, 0.30)
    assert porosity(coating_density(18, t), true_rho) == pytest.approx(0.30)


def test_target_porosity_rejects_percent_instead_of_fraction():
    with pytest.raises(ValueError):
        density_for_target_porosity(4.0, 30)  # 30 instead of 0.30
    with pytest.raises(ValueError):
        density_for_target_porosity(4.0, 1.0)


# --- N/P design helpers -------------------------------------------------------

def test_required_loading_is_inverse_of_areal_capacity():
    # 2.0 mAh/cm^2 from 200 mAh/g at 100 % active -> 10 mg/cm^2
    assert required_loading(2.0, 200, 1.0) == pytest.approx(10.0)
    assert areal_capacity(150, required_loading(2.85, 150, 0.95), 0.95) == pytest.approx(2.85)


def test_required_anode_loading_hits_target_np():
    # N/P 1.1 against 2.0 mAh/cm^2 cathode, 350 mAh/g graphite at 95 %:
    # 1.1 * 2.0 / (350 * 0.95) * 1000 = 6.6165 mg/cm^2
    loading = required_anode_loading(1.1, 2.0, 350, 0.95)
    assert loading == pytest.approx(2.2 / 332.5 * 1000)
    assert np_ratio(areal_capacity(350, loading, 0.95), 2.0) == pytest.approx(1.1)


def test_required_cathode_loading_hits_target_np():
    # N/P 1.1 against 2.2 mAh/cm^2 anode, 200 mAh/g cathode at 100 % -> 10 mg/cm^2
    loading = required_cathode_loading(1.1, 2.2, 200, 1.0)
    assert loading == pytest.approx(10.0)
    assert np_ratio(2.2, areal_capacity(200, loading, 1.0)) == pytest.approx(1.1)


def test_required_loadings_reject_bad_input():
    with pytest.raises(ValueError):
        required_anode_loading(0, 2.0, 350)
    with pytest.raises(ValueError):
        required_anode_loading(1.1, 0, 350)
    with pytest.raises(ValueError):
        required_cathode_loading(1.1, 2.2, 0)
    with pytest.raises(ValueError):
        required_loading(2.0, 200, 1.5)


def test_reversible_capacity():
    # 220 mAh/g first charge at 90 % first-cycle efficiency -> 198 mAh/g
    assert reversible_capacity(220, 0.90) == pytest.approx(198.0)
    with pytest.raises(ValueError):
        reversible_capacity(220, 90)  # percent instead of fraction
    with pytest.raises(ValueError):
        reversible_capacity(-1, 0.9)


def test_area_corrected_np_ratio():
    # local N/P 1.2 with anode 5 % larger than cathode -> 1.26
    assert area_corrected_np_ratio(2.4, 2.0, 1.05) == pytest.approx(1.26)
    assert area_corrected_np_ratio(2.4, 2.0, 1.0) == pytest.approx(np_ratio(2.4, 2.0))
    with pytest.raises(ValueError):
        area_corrected_np_ratio(2.4, 2.0, 0)


@pytest.mark.parametrize("value, status", [
    (-0.1, "error"), (0.0, "error"), (0.95, "warning"), (1.02, "warning"),
    (1.10, "ok"), (1.05, "ok"), (1.20, "ok"), (1.35, "warning"),
])
def test_check_np_ratio(value, status):
    got_status, message = check_np_ratio(value)
    assert got_status == status
    assert f"{value:.2f}" in message
