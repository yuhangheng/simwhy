# Model scope, evidence and limitations

## What can this numerical result establish?

Given the stated numbers and the stated simplified equations, it computes a numerical trajectory and verifies basic implementation consistency. It cannot infer unique hardware parameters or establish whether a real vehicle can safely perform a maneuver.

### Equations and assumptions

Ideal gas: `pV=mRT`. Rigid fixed-volume tank, perfectly mixed, reversible adiabatic uniform thermodynamics (a strong assumption). For the tank: `p/p0=(m/m0)^gamma` and `T/T0=(m/m0)^(gamma-1)`.

For pressure ratio `p_amb/p_tank` below `(2/(gamma+1))^(gamma/(gamma-1))`, use ideal convergent choking. Mass flow:
`mdot = Cd A p0 sqrt(gamma/(R T0)) (2/(gamma+1))^((gamma+1)/(2(gamma-1)))`.
Exit speed `v_e = sqrt(gamma R T0 2/(gamma+1))`.
Nominal thrust `F = mdot v_e + (p_e-p_amb) A`, where `p_e=p0*(2/(gamma+1))^(gamma/(gamma-1))`.

At unchoked conditions use ideal isentropic subsonic exit relations (with `p_e=p_amb`). Use `Cd` in mass flow, not independently in the ideal velocity. The discharge coefficient is a modeling convention, not an experimental calibration.

Vertical point mass: `dv/dt=F/M-g`, `dy/dt=v`. Ground interaction is a unilateral, inelastic positional clamp. Semi-implicit Euler integration. Tank mass cannot fall below ambient-equilibrium adiabatic mass.

### Error categories

1. **Implementation/numerical error**: mass accounting and parameter validation; half-step recomputation of the peak. Ten executable tests cover selected invariants. Step convergence only assesses numerical timestep effect on this solver.
2. **Model form uncertainty (large, not quantified)**: nitrogen nonideality around 25 MPa; temperature gradients, transient valves, real nozzle performance, plumbing losses and gas thermal exchange; actual vehicle mass, tank geometry, aerodynamic and structural effects; omission of rotations and suction.
3. **Input uncertainty (large, not quantified)**: all parameters in the provided demonstration are fictitious illustrative selections. No access to manufacturer tank/nozzle specifications.
4. **Experimental validation**: NOT PERFORMED. No comparison with measured tank pressure traces, impulses, thrust stand data or flight telemetry.

**Consequently, do not interpret the 4.12 m calculation as an estimate of Tesla's demonstrated height, a real engineering prediction with confidence bounds, or a design recommendation.** High pressure can be hazardous; neither physical pressure-vessel construction nor operation is within scope.

### What would improve confidence?

Use a real-gas EOS, measured Cd(nozzle, pressure), tank blowdown test data, a 6DoF mass/inertia model, valve control traces and independently measured trajectory. For each incremental addition retain a public benchmark and error envelope. Confidence must be built on evidence, not declared from an LLM.
