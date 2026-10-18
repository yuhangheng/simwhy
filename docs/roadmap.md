# Short implementation roadmap (not a promise)

- **Done v0.1**: dependency-free vertical pulse; 10 unit/integration tests; two scenarios; CSV/JSON/SVG.
- **Next**: pressure/time parameter sweep, explicit model uncertainty, and checks against public nonproprietary compressed-gas discharge data.
- **Then**: rigid-body orientation dynamics with signed torques, power/mass budget and controller saturation; an independent toy stability reference.
- **Later**: open solver adapters (AeroSandbox/SU2, RocketPy, JSBSim), with low-cost validation cases. MATLAB/Simulink and Fluent are optional commercial adapters; published core does not require them.
- **Research**: paper-to-executable-contract workflow, benchmark test sets, agent autonomy and cost tracking, transparent failures.

Rules: a PR needs a runnable example, its input provenance, a deterministic test, and an explicit modeling-limit statement. Do not fill the repository with speculative descriptions before runnable work.
