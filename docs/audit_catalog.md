# SimWhy Audit — Failure-Case Catalog

The audit engine (`simwhy/audit.py`) implements 12 deterministic checks,
each grounded in a real failure observed across Case 001–003 of the
hypersonic inlet/engine coupling research.

| ID | Check | Severity | Real failure it catches |
|----|-------|----------|------------------------|
| FC-001 | Circular mass-flow definition | critical | Engine receives CFD `mdot` as input port; no relation returns required inlet pressure or demand `mdot`. (Case 002 `engine_fuel_mass_corrected.slx` port 4) |
| FC-002 | Backpressure not physically established | critical | Specified BPR does not control core flow; exit remains supersonic. (Case 002 BPR 1.0–5.0, exit Ma 2.8–2.9) |
| FC-003 | Shock train not detected | warning | No shock train forms for any BPR; isolator cannot develop pressure rise. (Case 002, dp/dx oscillations ~35, constant) |
| FC-004 | Mass imbalance at high BPR | warning | `mass_defect_pct > 1%` indicates flow breakdown, not controlled response. (Case 002 BPR=8.0, 3.15% imbalance, 55% backflow) |
| FC-005 | Supersonic exit with pressure-outlet | critical | Exit Mach > 1 means specified static pressure is NOT enforced by the solver (Fluent extrapolates from interior). (Case 002) |
| FC-006 | Non-finite signals | critical | NaN/Inf in signal logs indicates numerical breakdown. (Case 002 passed: 0 non-finite columns) |
| FC-007 | FER step does not reach engine | critical | FER perturbation should produce a measurable thrust change; if `|ΔT| < 1 N` the coupling is broken. (Case 003 M2: ΔT = 64.6 N, OK) |
| FC-008 | Gas-model inconsistency | warning | `cp` or `γ` mismatch between CFD and engine. (CFD cp=1006.43, engine cp=1004; CFD γ=1.399, engine γ=1.4) |
| FC-009 | Span parameter labeling | warning | 2D→3D span conversion (0.4306 m) must be labeled as a research parameter, not real X-43A geometry. |
| FC-010 | Unvalidated parametric hypothesis | warning | Combustor pressure recovery `sigma_combustor=0.95` is a hypothesis; must be explicitly labeled, not silently embedded. |
| FC-011 | Report contradicts native data | critical | A numeric claim in a written report (e.g. `FINAL_RESULT.md`) that disagrees with the native metrics JSON beyond a stated tolerance. |
| FC-012 | No native evidence for the claim | warning | A CFD/Simulink claim with no native case/data, transcript, MAT or SLX artifact behind it. |

## Defects fixed in this revision

1. **FC-004 percent/fraction confusion.** The column `mass_defect_pct` holds a
   PERCENT (3.15 means 3.15 %), but the check compared it with `0.01`. Every run
   with more than 0.01 % defect was flagged, i.e. the threshold was 100x too
   strict. The threshold is now `> 1.0` percent, and `*_frac` columns are
   converted explicitly. Column matching is case-insensitive.

2. **Empty directory returned `AUDIT_PASSED`.** With nothing to inspect, every
   check degraded to "skip" and the verdict was a pass. `AuditReport` now
   returns `AUDIT_INCONCLUSIVE` when no check ran, and FC-012 warns when no
   native evidence exists.

3. **Report/native disagreement could still pass.** FC-011 now extracts
   unambiguous numeric claims from the reports and fails when they contradict
   the native metrics.

4. **No rule for real Fluent/Simulink/engine-matching evidence.** FC-012 adds
   it, and the artifact patterns are configurable per experiment through an
   optional `audit_rules.json`:

   ```json
   { "native_evidence": { "enabled": true,
                          "patterns": ["*.cas.h5", "*.dat.h5", "*.trn",
                                       "*.mat", "*.slx", "metrics.json"] } }
   ```

## Usage

```bash
# audit a coupled-simulation directory
python -m simwhy audit <directory> --format text
python -m simwhy audit <directory> --format json

# exit code: 1 if any critical failure is present
```

The audit is dependency-free (Python 3.10+, stdlib only) and does NOT run
simulations. It inspects files and matches structural / numerical patterns.

## Running the regression tests

```bash
python -m unittest discover -s tests -v
```

33 audit tests + 10 core tests cover every check above (both the
failure-triggering and the pass/skip branch), including the four
counter-example regressions for the defects fixed above.
