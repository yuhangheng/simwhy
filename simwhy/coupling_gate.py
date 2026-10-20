"""Dependency-free *screening* for CFD backpressure and dynamic feedback evidence.

This module cannot certify physical coupling. It detects when purported evidence
does not even demonstrate resolvable fixed-geometry CFD response or a causal
pressure-feedback path. Inputs are derived tables/traces, not native solver files.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Mapping


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: expected finite numeric value")
    x = float(value)
    if not math.isfinite(x):
        raise ValueError(f"{name}: non-finite value")
    return x


def _series(obj, key):
    v = obj.get(key)
    if not isinstance(v, list) or not v:
        raise ValueError(f"{key}: nonempty numeric array required")
    return [_number(x, key) for x in v]


def _different(a, b, *, atol=1e-9):
    return any(abs(x - y) > atol for x, y in zip(a, b))


def assess_backpressure(cases, *, max_mass_imbalance_pct=1.0, min_signal_to_drift=3.0):
    """Detect an upstream response at *fixed geometry*, above iteration drift.

    Numerical tolerances are conservative example acceptance parameters, NOT
    solver-independent physical laws. Cases must be from independent CFD solves.
    """
    max_mass_imbalance_pct = _number(max_mass_imbalance_pct, "max_mass_imbalance_pct")
    min_signal_to_drift = _number(min_signal_to_drift, "min_signal_to_drift")
    if max_mass_imbalance_pct <= 0 or min_signal_to_drift <= 0:
        raise ValueError("thresholds must be positive")
    if not isinstance(cases, list):
        raise ValueError("cfd_cases: array required")
    groups = defaultdict(list)
    for n, case in enumerate(cases):
        if not isinstance(case, dict) or not isinstance(case.get("geometry_id"), str) or not case["geometry_id"].strip():
            raise ValueError(f"case {n}: geometry_id required")
        row = {
            "geometry_id": case["geometry_id"],
            "backpressure_pa": _number(case.get("backpressure_pa"), "backpressure_pa"),
            "upstream_pressure_pa": _number(case.get("upstream_pressure_pa"), "upstream_pressure_pa"),
            "iteration_drift_pa": _number(case.get("iteration_drift_pa"), "iteration_drift_pa"),
            "mass_imbalance_pct": _number(case.get("mass_imbalance_pct"), "mass_imbalance_pct"),
        }
        if row["iteration_drift_pa"] < 0:
            raise ValueError("iteration_drift_pa must be >= 0")
        groups[row["geometry_id"]].append(row)
    pairs = []
    for geometry, rows in groups.items():
        for i, a in enumerate(rows):
            for b in rows[i + 1:]:
                dp_back = abs(a["backpressure_pa"] - b["backpressure_pa"])
                if dp_back <= 1e-9:
                    continue
                dp_up = abs(a["upstream_pressure_pa"] - b["upstream_pressure_pa"])
                drift = max(a["iteration_drift_pa"], b["iteration_drift_pa"])
                trustworthy_balance = max(abs(a["mass_imbalance_pct"]), abs(b["mass_imbalance_pct"])) <= max_mass_imbalance_pct
                resolved = dp_up > min_signal_to_drift * drift if drift > 0 else dp_up > 0
                pairs.append({
                    "geometry_id": geometry,
                    "delta_backpressure_pa": dp_back,
                    "delta_upstream_pressure_pa": dp_up,
                    "drift_bound_pa": drift,
                    "max_mass_imbalance_pct": max(abs(a["mass_imbalance_pct"]), abs(b["mass_imbalance_pct"])),
                    "resolved_above_drift": resolved,
                    "balance_within_target": trustworthy_balance,
                    "usable_numeric_pair": resolved and trustworthy_balance,
                })
    if not pairs:
        status = "INSUFFICIENT_FIXED_GEOMETRY_SWEEP"
    elif any(p["usable_numeric_pair"] for p in pairs):
        status = "RESOLVED_NUMERIC_UPSTREAM_RESPONSE"
    elif any(p["resolved_above_drift"] for p in pairs):
        status = "RESPONSE_WITH_UNACCEPTABLE_BALANCE"
    else:
        status = "NO_RESOLVED_UPSTREAM_RESPONSE"
    return {"status": status, "pairs": pairs, "warning": "Numerical response is not proof of causal backpressure physics or mesh independence."}


def assess_pressure_ablation(nominal, pressure_off, *, min_inlet_delta_pa=0.1, min_thrust_delta_n=0.1):
    """Compare synchronous actual outputs with pressure feedback enabled/disabled.

    The same external command must reach both runs. No claim can be inferred
    without a nonzero pressure-command excitation.
    """
    if not isinstance(nominal, Mapping) or not isinstance(pressure_off, Mapping):
        raise ValueError("nominal and pressure_off runs required")
    for k in ("time_s", "pressure_command_pa", "inlet_pressure_pa", "thrust_n"):
        a = _series(nominal, k)
        b = _series(pressure_off, k)
        if len(a) != len(b) or any(abs(x - y) > 1e-9 for x, y in zip(a if k == "time_s" else [], b if k == "time_s" else [])):
            raise ValueError(f"{k}: incompatible sample counts or time grids")
        if k == "pressure_command_pa" and _different(a, b):
            raise ValueError("different imposed pressure command between ablation runs")
    times = _series(nominal, "time_s")
    if len(times) < 2 or any(t2 <= t1 for t1, t2 in zip(times, times[1:])):
        raise ValueError("time_s: at least two increasing samples required")
    cmd = _series(nominal, "pressure_command_pa")
    inlet_diff = max(abs(x-y) for x,y in zip(_series(nominal,"inlet_pressure_pa"),_series(pressure_off,"inlet_pressure_pa")))
    thrust_diff = max(abs(x-y) for x,y in zip(_series(nominal,"thrust_n"),_series(pressure_off,"thrust_n")))
    excited = max(cmd) - min(cmd) > 1e-9
    min_inlet_delta_pa = _number(min_inlet_delta_pa, "min_inlet_delta_pa")
    min_thrust_delta_n = _number(min_thrust_delta_n, "min_thrust_delta_n")
    if min_inlet_delta_pa < 0 or min_thrust_delta_n < 0:
        raise ValueError("minimum effects must be nonnegative")
    if not excited:
        status = "NO_PRESSURE_EXCITATION"
    elif inlet_diff <= min_inlet_delta_pa and thrust_diff <= min_thrust_delta_n:
        status = "PRESSURE_FEEDBACK_NO_MEASURABLE_EFFECT"
    elif inlet_diff > min_inlet_delta_pa and thrust_diff > min_thrust_delta_n:
        status = "NUMERICALLY_SENSITIVE_NOT_PHYSICALLY_VALIDATED"
    else:
        status = "PARTIAL_NUMERIC_SENSITIVITY"
    return {
        "status": status,
        "pressure_command_span_pa": max(cmd) - min(cmd),
        "max_inlet_pressure_delta_pa": inlet_diff,
        "max_thrust_delta_n": thrust_diff,
        "warning": "Nonzero ablation only shows implemented numerical sensitivity; conservation and source physics remain separate."
    }


def assess_evidence(payload):
    if not isinstance(payload, dict):
        raise ValueError("root JSON must be an object")
    settings = payload.get("thresholds", {})
    if not isinstance(settings, dict):
        raise ValueError("thresholds must be an object")
    cfd = assess_backpressure(payload.get("cfd_cases", []),
                             max_mass_imbalance_pct=settings.get("max_mass_imbalance_pct", 1.0),
                             min_signal_to_drift=settings.get("min_signal_to_drift", 3.0))
    ablation_data = payload.get("pressure_ablation")
    if ablation_data is None:
        ablation = {"status": "NO_ABLATION_EVIDENCE"}
    else:
        if not isinstance(ablation_data, dict):
            raise ValueError("pressure_ablation must be an object")
        ablation = assess_pressure_ablation(
            ablation_data.get("nominal"), ablation_data.get("pressure_off"),
            min_inlet_delta_pa=settings.get("min_inlet_delta_pa", 0.1),
            min_thrust_delta_n=settings.get("min_thrust_delta_n", 0.1),
        )
    joint = (cfd["status"] == "RESOLVED_NUMERIC_UPSTREAM_RESPONSE" and
             ablation["status"] == "NUMERICALLY_SENSITIVE_NOT_PHYSICALLY_VALIDATED")
    return {
        "verdict": "NUMERICALLY_SUPPORTED_REQUIRES_PHYSICAL_VALIDATION" if joint else "PHYSICAL_COUPLING_NOT_VALIDATED",
        "cfd": cfd, "pressure_ablation": ablation,
        "limits": ["Does not read original CFD/Simulink binary data or prove provenance.",
                   "Does not verify conservation equations, mesh independence, or inlet/engine compatibility.",
                   "Thresholds are analyst-defined, not universal physical criteria."],
    }
