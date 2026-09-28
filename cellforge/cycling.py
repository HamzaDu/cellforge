"""
Cycling analysis: turn raw cycler data (time, current, voltage) into per-cycle results.

Works on plain Python sequences (lists, tuples, numpy arrays) - no extra dependencies.

Units:
    time      s
    current   mA   (positive = charge, negative = discharge; BioLogic convention)
    voltage   V
    capacity  mAh  (specific capacity mAh/g when an active mass is given)
    energy    mWh

Conventions (same as OperaXN, WMG):
    - A point is "charge" if current > threshold, "discharge" if current < -threshold,
      otherwise "rest". Rests are ignored for capacity.
    - Capacity is the trapezoidal integral of |I| dt within each phase; it restarts
      at the start of every charge / discharge phase.
    - A cycle starts at the first charge (or discharge, see first_step) and ends
      just before the next one. Anything before the first step is cycle 0 and ignored.
"""

from math import isfinite

CHARGE, DISCHARGE, REST = "charge", "discharge", "rest"
DEFAULT_CURRENT_THRESHOLD_MA = 1e-6


def _validate_series(time_s, current_ma, voltage_v=None):
    n = len(time_s)
    if n != len(current_ma) or (voltage_v is not None and n != len(voltage_v)):
        raise ValueError("time, current (and voltage) must have the same length")
    if n < 2:
        raise ValueError("At least two data points are needed")
    for a, b in zip(time_s, time_s[1:]):
        if b < a:
            raise ValueError("Time must not go backwards")


def classify_points(current_ma, threshold_ma: float = DEFAULT_CURRENT_THRESHOLD_MA) -> list:
    """Label each point 'charge', 'discharge' or 'rest' from the sign of the current."""
    if threshold_ma < 0:
        raise ValueError("Threshold must be non-negative")
    return [CHARGE if i > threshold_ma else DISCHARGE if i < -threshold_ma else REST for i in current_ma]


def assign_cycles(current_ma, first_step: str = CHARGE, threshold_ma: float = DEFAULT_CURRENT_THRESHOLD_MA) -> list:
    """
    Cycle number for each point.

    A new cycle starts each time a `first_step` phase begins after the other phase
    (or at the very first `first_step`). Use first_step='discharge' for anode
    half-cells or cells that start by discharging.
    """
    if first_step not in (CHARGE, DISCHARGE):
        raise ValueError("first_step must be 'charge' or 'discharge'")
    phases = classify_points(current_ma, threshold_ma)
    cycles, cycle, last_active = [], 0, None
    for p in phases:
        if p == first_step and last_active != first_step:
            cycle += 1
        if p != REST:
            last_active = p
        cycles.append(cycle)
    return cycles


def integrate_capacity(time_s, current_ma) -> float:
    """
    Total capacity (mAh) passed: trapezoidal integral of |I| over time.

    Q (mAh) = sum( (|I_k| + |I_k+1|) / 2 * (t_k+1 - t_k) ) / 3600
    """
    _validate_series(time_s, current_ma)
    total = 0.0
    for k in range(len(time_s) - 1):
        total += (abs(current_ma[k]) + abs(current_ma[k + 1])) / 2 * (time_s[k + 1] - time_s[k])
    return total / 3600


def cycle_summary(time_s, current_ma, voltage_v=None, active_mass_mg: float = None,
                  first_step: str = CHARGE, threshold_ma: float = DEFAULT_CURRENT_THRESHOLD_MA) -> list:
    """
    Per-cycle charge/discharge capacity, coulombic efficiency and (optionally) energy.

    Args:
        time_s, current_ma: Cycler data (seconds, mA; positive current = charge)
        voltage_v: Optional voltage (V) - adds energy (mWh) and average voltages
        active_mass_mg: Optional active material mass (mg) - adds specific capacity (mAh/g)
        first_step: 'charge' (default, cathode/full cell) or 'discharge' (e.g. anode half-cell)
        threshold_ma: |current| at or below this is treated as rest

    Returns:
        List of dicts, one per cycle (cycle 0, before the first step, is skipped):
            cycle, charge_capacity_mah, discharge_capacity_mah, coulombic_efficiency,
            [charge/discharge_specific_capacity_mah_g], [charge/discharge_energy_mwh,
            average_charge/discharge_voltage_v]
        Coulombic efficiency is discharge / charge (or charge / discharge when
        first_step='discharge'); None if the second half of the cycle is missing.
    """
    _validate_series(time_s, current_ma, voltage_v)
    if active_mass_mg is not None and active_mass_mg <= 0:
        raise ValueError("Active mass must be positive")
    phases = classify_points(current_ma, threshold_ma)
    cycles = assign_cycles(current_ma, first_step, threshold_ma)

    results = {}
    for k in range(len(time_s) - 1):
        phase, cycle = phases[k + 1], cycles[k + 1]
        if cycle == 0 or phase == REST or phases[k] != phase:
            continue  # only integrate within one charge/discharge phase
        dt = time_s[k + 1] - time_s[k]
        dq = (abs(current_ma[k]) + abs(current_ma[k + 1])) / 2 * dt / 3600  # mAh
        row = results.setdefault(cycle, {"cycle": cycle, "charge_capacity_mah": 0.0, "discharge_capacity_mah": 0.0,
                                          "charge_energy_mwh": 0.0, "discharge_energy_mwh": 0.0})
        row[f"{phase}_capacity_mah"] += dq
        if voltage_v is not None:
            v_avg = (voltage_v[k] + voltage_v[k + 1]) / 2
            row[f"{phase}_energy_mwh"] += dq * v_avg

    summary = []
    for cycle in sorted(results):
        row = results[cycle]
        q_ch, q_dis = row["charge_capacity_mah"], row["discharge_capacity_mah"]
        first, second = (q_ch, q_dis) if first_step == CHARGE else (q_dis, q_ch)
        out = {"cycle": cycle, "charge_capacity_mah": q_ch, "discharge_capacity_mah": q_dis,
               "coulombic_efficiency": (second / first) if first > 0 and second > 0 else None}
        if active_mass_mg is not None:
            out["charge_specific_capacity_mah_g"] = q_ch / (active_mass_mg / 1000)
            out["discharge_specific_capacity_mah_g"] = q_dis / (active_mass_mg / 1000)
        if voltage_v is not None:
            out["charge_energy_mwh"] = row["charge_energy_mwh"]
            out["discharge_energy_mwh"] = row["discharge_energy_mwh"]
            out["average_charge_voltage_v"] = row["charge_energy_mwh"] / q_ch if q_ch > 0 else None
            out["average_discharge_voltage_v"] = row["discharge_energy_mwh"] / q_dis if q_dis > 0 else None
        summary.append(out)
    return summary


def capacity_retention(capacities, reference_index: int = 0) -> list:
    """
    Capacity retention (fraction of the reference cycle), e.g. [1.0, 0.99, 0.985, ...].

    Args:
        capacities: Capacities per cycle, e.g. [row['discharge_capacity_mah'] for row in summary]
        reference_index: Which cycle to compare against (0 = first in the list). Use 1 or 2
            to exclude formation cycles.
    """
    if not capacities:
        raise ValueError("No capacities given")
    ref = capacities[reference_index]
    if ref is None or ref <= 0:
        raise ValueError("Reference capacity must be positive")
    return [None if c is None else c / ref for c in capacities]


def formation_summary(time_s, current_ma, voltage_v=None, active_mass_mg: float = None,
                      first_step: str = CHARGE, threshold_ma: float = DEFAULT_CURRENT_THRESHOLD_MA) -> dict:
    """
    First-cycle (formation) results in one call.

    Returns:
        dict with first_charge_capacity_mah, first_discharge_capacity_mah,
        first_cycle_efficiency (ICE, fraction) and irreversible_capacity_mah,
        plus specific capacities if active_mass_mg is given.
        This maps onto Hazbat's formation_capacity field (first discharge capacity).
    """
    summary = cycle_summary(time_s, current_ma, voltage_v, active_mass_mg, first_step, threshold_ma)
    if not summary:
        raise ValueError("No complete cycle found in the data")
    c1 = summary[0]
    q_ch, q_dis = c1["charge_capacity_mah"], c1["discharge_capacity_mah"]
    first, second = (q_ch, q_dis) if first_step == CHARGE else (q_dis, q_ch)
    out = {
        "first_charge_capacity_mah": q_ch,
        "first_discharge_capacity_mah": q_dis,
        "first_cycle_efficiency": c1["coulombic_efficiency"],
        "irreversible_capacity_mah": (first - second) if second > 0 else None,
    }
    if active_mass_mg is not None:
        out["first_charge_specific_capacity_mah_g"] = c1["charge_specific_capacity_mah_g"]
        out["first_discharge_specific_capacity_mah_g"] = c1["discharge_specific_capacity_mah_g"]
    return out


# Column names used by galvani for BioLogic .mpr files (first match wins)
_MPR_COLUMNS = {
    "time": ("time/s",),
    "current": ("I/mA", "control/mA", "<I>/mA"),
    "voltage": ("Ewe/V", "<Ewe>/V", "Ecell/V"),
}


def columns_from_mpr(data) -> tuple:
    """
    Pull (time_s, current_ma, voltage_v) out of a BioLogic .mpr table read by galvani.

    Usage (in Hazbat, which already has galvani installed):
        from galvani import BioLogic
        mpr = BioLogic.MPRfile(path)
        t, i, v = columns_from_mpr(mpr.data)
        formation_summary(t, i, v, active_mass_mg=...)

    `data` can be any table with named columns (numpy structured array, dict, DataFrame).
    Voltage is None if no voltage column is found.
    """
    names = list(data.dtype.names) if hasattr(data, "dtype") and data.dtype.names else list(data.keys())
    found = {}
    for key, candidates in _MPR_COLUMNS.items():
        found[key] = next((c for c in candidates if c in names), None)
    if found["time"] is None or found["current"] is None:
        raise ValueError(f"Couldn't find time/current columns; available columns: {names}")
    t = [float(x) for x in data[found["time"]]]
    i = [float(x) for x in data[found["current"]]]
    v = [float(x) for x in data[found["voltage"]]] if found["voltage"] else None
    if not all(isfinite(x) for x in t + i):
        raise ValueError("Time/current contain non-numeric values")
    return t, i, v
