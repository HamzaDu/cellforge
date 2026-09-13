import pytest
from cellforge.electrode import areal_capacity, np_ratio


def test_areal_capacity_basic():
    # 200 mAh/g material, 10 mg/cm^2 loading, 100% active material
    # 200 * 0.010 * 1.0 = 2.0 mAh/cm^2
    assert areal_capacity(200, 10, 1.0) == pytest.approx(2.0)


def test_areal_capacity_with_fraction():
    # 150 mAh/g, 20 mg/cm^2, 95% active material
    # 150 * 0.020 * 0.95 = 2.85 mAh/cm^2
    assert areal_capacity(150, 20, 0.95) == pytest.approx(2.85)


def test_areal_capacity_rejects_negative():
    with pytest.raises(ValueError):
        areal_capacity(-100, 10)
    with pytest.raises(ValueError):
        areal_capacity(100, -10)


def test_areal_capacity_rejects_bad_fraction():
    with pytest.raises(ValueError):
        areal_capacity(100, 10, 0)
    with pytest.raises(ValueError):
        areal_capacity(100, 10, 1.5)


def test_np_ratio_basic():
    # anode 2.4 mAh/cm^2, cathode 2.0 mAh/cm^2 -> N/P = 1.2
    assert np_ratio(2.4, 2.0) == pytest.approx(1.2)


def test_np_ratio_rejects_zero_cathode():
    with pytest.raises(ValueError):
        np_ratio(2.0, 0)


def test_np_ratio_rejects_negative_anode():
    with pytest.raises(ValueError):
        np_ratio(-1.0, 2.0)
        