import pytest
from cellforge.cycling import (
    classify_points, assign_cycles, integrate_capacity, cycle_summary,
    capacity_retention, formation_summary, columns_from_mpr,
)


def build_cycles(discharge_currents=(-1.0, -0.9), leading_rest=3, active=10, rest=5,
                 v_charge=4.0, v_discharge=3.5):
    """Synthetic cycler data at 1 s steps: [rest] + per cycle: +1 mA charge, rest, discharge, rest.

    Each phase has `active` points, i.e. active-1 one-second intervals, so a 1 mA phase
    integrates to exactly (active-1)/3600 mAh.
    """
    current, voltage = [0.0] * leading_rest, [3.0] * leading_rest
    for i_dis in discharge_currents:
        current += [1.0] * active + [0.0] * rest + [i_dis] * active + [0.0] * rest
        voltage += [v_charge] * active + [3.8] * rest + [v_discharge] * active + [3.2] * rest
    time = [float(s) for s in range(len(current))]
    return time, current, voltage


Q9 = 9 / 3600  # mAh for 1 mA over 9 s


def test_classify_points():
    assert classify_points([1.0, 0.0, -2.0, 1e-9]) == ["charge", "rest", "discharge", "rest"]


def test_assign_cycles_leading_rest_is_cycle_zero():
    t, i, v = build_cycles()
    cycles = assign_cycles(i)
    assert cycles[:3] == [0, 0, 0]
    assert sorted(set(cycles) - {0}) == [1, 2]


def test_assign_cycles_discharge_first():
    t, i, v = build_cycles()
    flipped = [-x for x in i]  # now the cell discharges first
    assert sorted(set(assign_cycles(flipped, first_step="discharge")) - {0}) == [1, 2]


def test_integrate_capacity_constant_current():
    # 2 mA for 1 h sampled every 10 s -> 2 mAh
    t = [10.0 * k for k in range(361)]
    assert integrate_capacity(t, [2.0] * 361) == pytest.approx(2.0)


def test_integrate_capacity_uses_absolute_current():
    assert integrate_capacity([0, 3600], [-1.0, -1.0]) == pytest.approx(1.0)


def test_cycle_summary_capacities_and_efficiency():
    t, i, v = build_cycles()
    s = cycle_summary(t, i)
    assert [row["cycle"] for row in s] == [1, 2]
    assert s[0]["charge_capacity_mah"] == pytest.approx(Q9)
    assert s[0]["discharge_capacity_mah"] == pytest.approx(Q9)
    assert s[0]["coulombic_efficiency"] == pytest.approx(1.0)
    assert s[1]["discharge_capacity_mah"] == pytest.approx(0.9 * Q9)
    assert s[1]["coulombic_efficiency"] == pytest.approx(0.9)


def test_cycle_summary_specific_capacity_and_energy():
    t, i, v = build_cycles()
    s = cycle_summary(t, i, v, active_mass_mg=0.01)  # 10 ug
    assert s[0]["charge_specific_capacity_mah_g"] == pytest.approx(Q9 / 1e-5)
    assert s[0]["charge_energy_mwh"] == pytest.approx(Q9 * 4.0)
    assert s[0]["average_charge_voltage_v"] == pytest.approx(4.0)
    assert s[0]["average_discharge_voltage_v"] == pytest.approx(3.5)


def test_cycle_summary_incomplete_last_cycle():
    t, i, v = build_cycles(discharge_currents=(-1.0,))
    t2, i2 = t + [t[-1] + 1 + k for k in range(5)], i + [1.0] * 5  # a charge with no discharge after it
    s = cycle_summary(t2, i2)
    assert s[-1]["cycle"] == 2 and s[-1]["coulombic_efficiency"] is None


def test_cycle_summary_rejects_bad_input():
    with pytest.raises(ValueError):
        cycle_summary([0, 1], [1.0])              # length mismatch
    with pytest.raises(ValueError):
        cycle_summary([0, 2, 1], [1.0, 1.0, 1.0])  # time goes backwards
    with pytest.raises(ValueError):
        cycle_summary([0, 1], [1.0, 1.0], active_mass_mg=0)


def test_capacity_retention():
    assert capacity_retention([2.0, 1.9, 1.8]) == pytest.approx([1.0, 0.95, 0.9])
    assert capacity_retention([2.5, 2.0, 1.9], reference_index=1) == pytest.approx([1.25, 1.0, 0.95])
    with pytest.raises(ValueError):
        capacity_retention([0.0, 1.0])


def test_formation_summary():
    t, i, v = build_cycles(discharge_currents=(-0.85, -1.0))
    f = formation_summary(t, i, v, active_mass_mg=0.01)
    assert f["first_charge_capacity_mah"] == pytest.approx(Q9)
    assert f["first_discharge_capacity_mah"] == pytest.approx(0.85 * Q9)
    assert f["first_cycle_efficiency"] == pytest.approx(0.85)
    assert f["irreversible_capacity_mah"] == pytest.approx(0.15 * Q9)


def test_formation_summary_no_cycles():
    with pytest.raises(ValueError):
        formation_summary([0, 1, 2], [0.0, 0.0, 0.0])


def test_columns_from_mpr_dict():
    d = {"time/s": [0, 1], "I/mA": [1.0, 1.0], "Ewe/V": [3.9, 4.0]}
    assert columns_from_mpr(d) == ([0.0, 1.0], [1.0, 1.0], [3.9, 4.0])
    assert columns_from_mpr({"time/s": [0, 1], "I/mA": [1.0, 1.0]})[2] is None  # no voltage column
    with pytest.raises(ValueError):
        columns_from_mpr({"time/s": [0, 1]})  # no current column


def test_columns_from_mpr_structured_array():
    # galvani returns a numpy structured array; skip if numpy isn't installed
    np = pytest.importorskip("numpy")
    arr = np.array([(0.0, 1.0, 3.9), (1.0, 1.0, 4.0)], dtype=[("time/s", float), ("control/mA", float), ("Ewe/V", float)])
    t, i, v = columns_from_mpr(arr)
    assert i == [1.0, 1.0] and v == [3.9, 4.0]
