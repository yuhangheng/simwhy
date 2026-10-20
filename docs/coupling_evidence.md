# Coupling evidence screen (not a physical-validation certificate)

Use this dependency-free command to reject two recurring false-positive patterns
in simulation projects: **(1)** a purported backpressure sweep that only changes
geometry or only changes its outlet pressure, without an upstream response above
solver drift, and **(2)** a feedback wire that makes no numerical difference
when disconnected.

```bash
python -m simwhy coupling-audit examples/coupling_evidence_synthetic.json --format json
```

The included JSON is **synthetic**, must return `PHYSICAL_COUPLING_NOT_VALIDATED`,
and does not disclose or reproduce private project data.

## Input contract

The JSON root accepts:
- `cfd_cases[]`: `geometry_id`, `backpressure_pa`, `upstream_pressure_pa`,
  `iteration_drift_pa`, `mass_imbalance_pct` (percentage, not a fraction).
  At least two distinct imposed pressures at the **same geometry** are required.
  All pressures are absolute, measured at the same physical upstream station.
  Drift is a nonnegative independent continuing-iteration estimate.
- `pressure_ablation.nominal` and `pressure_ablation.pressure_off`: synchronized
  `time_s`, `pressure_command_pa`, `inlet_pressure_pa`, `thrust_n` arrays.
  Hold all input commands and other settings identical; only disable the pressure
  feedback branch in the second run.
- Optional `thresholds`: `max_mass_imbalance_pct` (example default 1.0),
  `min_signal_to_drift` (example default 3),
  `min_inlet_delta_pa` (example default 0.1) and
  `min_thrust_delta_n` (example default 0.1).
  **Thresholds are study-specific and must be justified**, not tuned to force PASS.

The screen checks numerical response, not causal aerodynamics. Even when both
tests show measurable differences, the strongest possible verdict is
`NUMERICALLY_SUPPORTED_REQUIRES_PHYSICAL_VALIDATION`. This is **not** a
`VALIDATED` physical coupling result.

Additional requirements before a credible *physical* claim include real native
solver provenance, independent conservation monitoring, comparison against
iteration drift and mesh uncertainty, verification of pressure propagation
paths and shock motion, physically derived interface/control-volume equations,
consistent station definitions, and independent validation conditions.

The ablation traces must come from **actual consumed engine/inlet signals**;
unconnected ports or renamed upstream signal probes do not count. An unexcited
ablation cannot establish either presence or absence of a pressure path.
For time series from different solver step grids, resample carefully outside
this checker and document the method; mismatched sample grids are rejected here.

## Why it matters

A pressure-outlet setpoint need not control the supersonic core, and a
three-point geometry scan at one imposed pressure cannot identify a pressure
response derivative at fixed geometry. Likewise, a Simulink block can execute
successfully despite an unused feedback input.

A pressure state should originate from appropriate mass and energy balances:
`dm/dt = mdot_in - mdot_out` and, for a fixed-volume ideal-gas plenum,
`dU/dt = sum(mdot_in*h_in) - sum(mdot_out*h_out) + Qdot`,
`p=(gamma-1)*U/V` for a constant-gamma calorically perfect gas.
This simplified illustration is not a substitute for a validated combustor
model or for the volume, heat and pressure data.

See Ansys Fluent documentation on convergence monitoring:
https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/flu_ug/flu_ug_sec_solve_monitor.html

## Relevant external literature (not evidence for this repository's case)

- R. I. Paek (2010), [Back-pressure Effect on Shock-Train Location in a Scramjet Engine Isolator](https://scholar.afit.edu/etd/2048/): experimental variable-area ramps and the relationship between back pressure, shock-train location, and unstart. This is motivation to distinguish imposed backpressure from measured upstream response.
- J. Lee and S. H. Kang (2019), [Numerical study on the start and unstart phenomena in a scramjet inlet-isolator model](https://doi.org/10.1371/journal.pone.0224994), *PLOS ONE*: a documented RANS isolator/inlet case that uses a downstream flap to simulate backpressure. It informs what a solver-backed pressure mechanism must demonstrate.
- [Ansys Fluent User's Guide: monitoring solution convergence](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/flu_ug/flu_ug_sec_solve_monitor.html): residual decline alone does not establish a settled physical solution; monitor conserved and integrated quantities too.

These are research references, **not reproduced or independently validated simulation outputs**. This repository does not include the authors' geometry, proprietary solvers, or research datasets.

## Source of generic lessons

This component abstracts failure modes seen while inspecting a multi-solver
aerospace simulation. It contains **no CFD/Simulink binaries, flight designs,
proprietary models, experiment-specific data or user-provided research files**.
The evidence schema and synthetic test case are deliberately general.
