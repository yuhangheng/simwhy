# Research software worth understanding

Curated manually from upstream GitHub README, selected source code and Issues. **Verified means the linked repository or stated documentation was inspected**, not that software was locally installed, tested or integrated. No wholesale vendoring, copying of third-party PDFs, or representation that these projects endorse SimWhy.

| Upstream | Primary strength | Relevant to SimWhy | Review depth |
|---|---|---|---|
| [ReproAgent](https://github.com/kernel-14/ReproAgent) | Evidence-grounded paper-to-code contracts | Map paper requirements to executable assertions | README |
| [ReproRepo](https://github.com/LithiumDA/ReproRepo) | Reproducibility audits grounded in paper/repo issues | Negative test cases and provenance | README |
| [PaperQA2](https://github.com/Future-House/paper-qa) | Literature retrieval and claim checking | Locate exact physics assumptions and citations | README |
| [AeroSandbox](https://github.com/peterdsharpe/AeroSandbox) | Aircraft design and differentiable optimization | Cheap aircraft benchmark cases | README + CI + selected Issues |
| [SU2](https://github.com/su2code/SU2) | Open compressible CFD / optimization | Cross-solver verification beyond commercial tools | README + SST config + Issues |
| [OpenMDAO](https://github.com/OpenMDAO/OpenMDAO) | Multidisciplinary analysis | Connect aero, propulsion and mission | README |
| [DAFoam](https://github.com/mdolab/dafoam) | Discrete adjoint design optimization | High-fidelity gradients / cost-aware future studies | README |
| [PyFR](https://github.com/PyFR/PyFR) | High-order computational fluid dynamics | Shock-capturing, independent solver reference | README + Navier-Stokes code |
| [OpenSBLI](https://github.com/opensbli/opensbli) | High-order compressible solver code generation | Transparent SBLI model research | README + manual + inflow Issue |
| [AirfRANS](https://github.com/Extrality/airfrans_lib) | Public airfoil RANS data | Reference ML field tasks; mind ODbL license | README |
| [RocketPy](https://github.com/RocketPy-Team/RocketPy) | Rocket flight simulation | Reusable, openly validated motion examples | README |
| [JSBSim](https://github.com/JSBSim-Team/jsbsim) | Aircraft/rocket flight dynamics | 6DoF aircraft cases and flight control | README |
| [NVIDIA PhysicsNeMo](https://github.com/NVIDIA/physicsnemo) | Physics AI and active learning | Surrogate uncertainty and informative simulations | README + active-learning recipe |
| [AI Scientist](https://github.com/SakanaAI/AI-Scientist) | Automated experiment templates | Bounded run and research iteration logic; sandbox needed | README + experiment driver source |
| [CMU agent-mcp](https://github.com/cmudrc/agent-mcp) | Aircraft engineering tool orchestration | Avoid replicating existing CPACS/solver interfaces | README + pipeline guide |
| [CMU agentic-bench](https://github.com/cmudrc/agentic-bench) | Agent tool-routing and numerical tests | Add stronger physics-grounded long-horizon trials | README + task YAML |
| [OpenAI MLE-bench](https://github.com/openai/mle-bench) | AI engineering competition benchmarking | Frozen tasks and grading contract discipline | README |
| [Microsoft Agent Lightning](https://github.com/microsoft/agent-lightning) | Learning from agent trajectories | Later training/reward design, not MVP | README |

Upstream projects have different licenses and computational prerequisites. Study each before using its code or datasets. Fluent/MATLAB interfaces, public literature, and other tool support are **not** implemented in this initial release.

## Source ideas / future contributions

Submit a GitHub Issue with (1) public URL/DOI and evidence type, (2) the physical mechanism you want explained, (3) a minimal parameterized simulation, (4) at least one independent analytic/invariant check, (5) data provenance and licensing, and (6) known limitations. Prefer concrete experiments and PRs over opinion essays.

## Public phenomenon sources used for v0.1 motivation

- [Aviation Week (2026-10-16)](https://aviationweek.com/aerospace/emerging-technologies/tesla-demos-flying-roadster-powered-spacex-cold-gas-thrusters): a Roadster prototype showed a short thruster-assisted hop and airborne maneuver.
- [Car and Driver (2026-10-17)](https://www.caranddriver.com/news/a74165059/tesla-roadster-thrusters-fan-system-explained/): reporting on cold gas and suction; **not** a primary engineering specification.
- Real internal nozzle arrangement, tank pressure, mass, valve actuation and flight control are not disclosed to this model. **Illustrative numbers here are not observations or inverse estimates.**
