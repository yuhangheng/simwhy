"""Small, auditable ideal-gas blowdown and vertical rigid-body model.

A deliberately simplified *hypothesis test*, NOT a Tesla or SpaceX digital twin.
See docs/assumptions.md before interpreting any result.
"""
from dataclasses import dataclass, asdict, replace
from math import ceil, isfinite, sqrt


@dataclass(frozen=True)
class Config:
    vehicle_mass_kg: float = 1600.0
    tank_volume_m3: float = 0.25
    tank_pressure_pa: float = 25_000_000.0
    tank_temperature_k: float = 300.0
    ambient_pressure_pa: float = 101_325.0
    throat_area_m2: float = 0.002
    discharge_coefficient: float = 0.90
    gas_constant_j_per_kg_k: float = 296.8  # nitrogen, illustrative
    gamma: float = 1.4
    valve_open_s: float = 0.45
    duration_s: float = 5.0
    dt_s: float = 0.002
    gravity_mps2: float = 9.80665

    @classmethod
    def from_dict(cls, mapping):
        unknown = set(mapping) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError("Unknown configuration parameters: " + ", ".join(sorted(unknown)))
        c = cls(**mapping)
        for key, value in asdict(c).items():
            if not isinstance(value, (int, float)) or not isfinite(value):
                raise ValueError(f"{key} must be a finite number")
        for key in ("vehicle_mass_kg", "tank_volume_m3", "tank_pressure_pa", "tank_temperature_k",
                    "ambient_pressure_pa", "throat_area_m2", "gas_constant_j_per_kg_k",
                    "duration_s", "dt_s", "gravity_mps2"):
            if getattr(c, key) <= 0:
                raise ValueError(f"{key} must be positive")
        if c.gamma <= 1:
            raise ValueError("gamma must exceed 1")
        if not 0 < c.discharge_coefficient <= 1:
            raise ValueError("discharge_coefficient must lie in (0, 1]")
        if c.tank_pressure_pa <= c.ambient_pressure_pa:
            raise ValueError("tank pressure must exceed ambient pressure")
        if not 0 <= c.valve_open_s <= c.duration_s:
            raise ValueError("valve_open_s must lie inside simulation duration")
        if c.duration_s / c.dt_s > 1_000_000:
            raise ValueError("Refusing more than 1,000,000 steps")
        return c


def nozzle_flow(p0, temperature, c):
    """Return (mass flow kg/s, thrust N, choked boolean).

    Convergent ideal-gas nozzle. Effective throat/exit area assumed equal.
    Nozzle pressure thrust is included for choked discharge. No shocks inside
    nozzle, valve transients, or real-gas/high-pressure effects.
    """
    if p0 <= c.ambient_pressure_pa or temperature <= 0:
        return 0.0, 0.0, False
    g, r, pa = c.gamma, c.gas_constant_j_per_kg_k, c.ambient_pressure_pa
    ratio = pa / p0
    critical = (2 / (g + 1)) ** (g / (g - 1))
    if ratio <= critical:
        massflow = (c.discharge_coefficient * c.throat_area_m2 * p0
                    * sqrt(g / (r * temperature))
                    * (2 / (g + 1)) ** ((g + 1) / (2 * (g - 1))))
        pe = p0 * critical
        te = temperature * 2 / (g + 1)
        ve = sqrt(g * r * te)
        thrust = massflow * ve + (pe - pa) * c.throat_area_m2
        return massflow, thrust, True
    bracket = max(0.0, ratio ** (2 / g) - ratio ** ((g + 1) / g))
    massflow = (c.discharge_coefficient * c.throat_area_m2 * p0
                * sqrt(2 * g / (r * temperature * (g - 1)) * bracket))
    ve = sqrt(max(0.0, 2 * g * r * temperature / (g - 1)
                  * (1 - ratio ** ((g - 1) / g))))
    return massflow, massflow * ve, False


def simulate(c):
    """Time-integrate a single vertical pulse and adiabatic tank blowdown.

    Semi-implicit Euler; ground contact is an inelastic clamp. For numerical
    error estimates compare with half-step integration (performed by CLI).
    """
    c = Config.from_dict(asdict(c))
    m0 = c.tank_pressure_pa * c.tank_volume_m3 / (
        c.gas_constant_j_per_kg_k * c.tank_temperature_k)
    m_eq = m0 * (c.ambient_pressure_pa / c.tank_pressure_pa) ** (1 / c.gamma)
    m, y, v, t, impulse, used = m0, 0.0, 0.0, 0.0, 0.0, 0.0
    first_flow, first_thrust, _ = nozzle_flow(c.tank_pressure_pa, c.tank_temperature_k, c)
    rows = []
    peak, peak_t, choked_steps = 0.0, 0.0, 0
    n = ceil(c.duration_s / c.dt_s)
    for i in range(n + 1):
        temp = c.tank_temperature_k * (m / m0) ** (c.gamma - 1)
        p = c.tank_pressure_pa * (m / m0) ** c.gamma
        if i == n:
            step = 0
        else:
            step = min(c.dt_s, c.duration_s - t)
        mdot, force, choked = nozzle_flow(p, temp, c) if t < c.valve_open_s - 1e-12 else (0.0, 0.0, False)
        rows.append({
            "time_s": round(t, 9), "altitude_m": y, "vertical_velocity_mps": v,
            "tank_pressure_pa": p, "tank_temperature_k": temp, "gas_remaining_kg": m,
            "massflow_kgps": mdot, "thrust_n": force
        })
        if not step:
            break
        allowed = max(0.0, m - m_eq)
        discharge = min(allowed, mdot * step)
        actual_force = force * (discharge / (mdot * step)) if mdot > 0 else 0.0
        m -= discharge
        used += discharge
        if choked and discharge > 0:
            choked_steps += 1
        accel = actual_force / c.vehicle_mass_kg - c.gravity_mps2
        v += accel * step
        y += v * step
        if y < 0:
            y, v = 0.0, 0.0
        if y <= 0 and v < 0:
            v = 0.0
        impulse += actual_force * step
        t = min(c.duration_s, t + step)
        if y > peak:
            peak, peak_t = y, t
    gas_balance = abs((m0 - m) - used)
    summary = {
        "status": "SIMULATION_ONLY_NOT_HARDWARE_VALIDATED",
        "peak_altitude_m": peak, "peak_time_s": peak_t,
        "initial_thrust_n": first_thrust,
        "initial_thrust_to_weight": first_thrust / (c.vehicle_mass_kg * c.gravity_mps2),
        "initial_massflow_kgps": first_flow,
        "initial_gas_kg": m0, "gas_consumed_kg": used, "gas_left_kg": m,
        "total_upward_thrust_impulse_ns": impulse,
        "choked_steps": choked_steps,
        "ideal_potential_energy_at_peak_j": c.vehicle_mass_kg * c.gravity_mps2 * peak,
        "numerical_mass_balance_error_kg": gas_balance,
        "discretization": "semi-implicit Euler; dt-refinement separately reported",
        "notes": [
            "Illustrative uniform-pressure ideal nitrogen model; not a Roadster reverse-engineering claim.",
            "Vertical point mass; excludes pitch/roll/yaw, traction, landing loads, drag and tank hardware.",
            "Independent agreement checks test implementation, not physical-model validity."
        ]
    }
    return rows, summary


def step_refinement(c):
    c = Config.from_dict(asdict(c))
    _, coarse = simulate(c)
    _, fine = simulate(replace(c, dt_s=c.dt_s / 2))
    a, b = coarse["peak_altitude_m"], fine["peak_altitude_m"]
    relative = abs(a - b) / max(abs(b), 1e-6)
    return {
        "coarse_dt_s": c.dt_s, "fine_dt_s": c.dt_s / 2,
        "coarse_peak_m": a, "fine_peak_m": b,
        "peak_difference_relative": relative,
        "dt_sensitivity_below_1pct": relative < 0.01,
        "warning": "Step-size agreement is numerical consistency, not experimental validation."
    }
