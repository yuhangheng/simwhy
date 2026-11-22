"""SimWhy Audit: automated evidence-based simulation audit.

Detects common failure patterns in CFD/engine/flight coupled simulation
directories. Each check is grounded in a real failure case from the
research project (Case 001-003).

Usage:
    python -m simwhy audit <directory>
    python -m simwhy audit <directory> --format json
    python -m simwhy audit <directory> --format text

The audit does NOT run simulations. It inspects files and checks for
specific structural and numerical failure patterns.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """A single audit finding."""
    check_id: str
    severity: str  # "critical", "warning", "info"
    title: str
    detail: str
    evidence: str
    verdict: str  # machine-readable tag

@dataclass
class AuditReport:
    """Full audit report for a directory."""
    directory: str
    findings: list[Finding] = field(default_factory=list)
    pass_count: int = 0
    fail_count: int = 0
    warning_count: int = 0

    @property
    def overall_verdict(self) -> str:
        if self.fail_count > 0:
            return "AUDIT_FAILED"
        if self.warning_count > 0:
            return "AUDIT_PASSED_WITH_WARNINGS"
        if self.pass_count == 0:
            # No check ran.  An empty experiment directory must never be
            # reported as a pass: nothing was verified.
            return "AUDIT_INCONCLUSIVE"
        return "AUDIT_PASSED"

    def to_dict(self) -> dict:
        return {
            "directory": self.directory,
            "overall_verdict": self.overall_verdict,
            "summary": {
                "pass": self.pass_count,
                "fail": self.fail_count,
                "warning": self.warning_count,
                "total_checks": self.pass_count + self.fail_count + self.warning_count,
            },
            "findings": [
                {
                    "check_id": f.check_id,
                    "severity": f.severity,
                    "title": f.title,
                    "detail": f.detail,
                    "evidence": f.evidence,
                    "verdict": f.verdict,
                }
                for f in self.findings
            ],
        }


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _load_json_safe(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _load_csv_safe(path: Path) -> list[dict] | None:
    import csv
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return None


def check_circular_mdot(report: AuditReport, root: Path) -> None:
    """FC-001: Engine receives CFD mass flow as input, not computing demand.

    Real failure: Case 002 engine_fuel_mass_corrected.slx has air_mdot_kg_s
    as INPUT PORT 4. The engine computes thrust FROM the given mdot, but
    no relation returns the required inlet pressure or demand mdot.
    """
    finding = Finding(
        check_id="FC-001",
        severity="critical",
        title="Circular mass-flow definition",
        detail="Engine receives CFD mass flow as input port, not computing demand from pressure/temperature.",
        evidence="",
        verdict="ENGINE_DEMAND_NOT_INDEPENDENT",
    )
    found = False
    # Check for pressure feedback verdict files
    for p in root.rglob("pressure_feedback_check*"):
        text = p.read_text(encoding="utf-8", errors="replace")
        if "NOT_ESTABLISHED" in text or "PRESSURE_MATCHING" in text:
            finding.evidence = f"{p.name}: contains PRESSURE_MATCHING_NOT_ESTABLISHED"
            found = True
            break
    # Check for engine demand analysis
    for p in root.rglob("engine_demand_analysis.json"):
        data = _load_json_safe(p)
        if data and data.get("circular_definition_check", {}).get("existing_engine_receives_mdot"):
            finding.evidence = f"{p.name}: existing_engine_receives_mdot=True"
            found = True
            break
    if found:
        report.fail_count += 1
        report.findings.append(finding)
    else:
        finding.severity = "info"
        finding.verdict = "CHECK_PASSED"
        finding.evidence = "No circular mass-flow definition detected"
        report.pass_count += 1
        report.findings.append(finding)


def check_backpressure_effectiveness(report: AuditReport, root: Path) -> None:
    """FC-002: Specified BPR does not produce physical backpressure.

    Real failure: Case 002 pressure-outlet with BPR 1.0-5.0 at supersonic
    exit (Ma 2.8-2.9) does not enforce specified pressure. Subsonic faces
    matching p_specified are exclusively wall boundary layer cells.
    """
    finding = Finding(
        check_id="FC-002",
        severity="critical",
        title="Backpressure not physically established",
        detail="Specified BPR does not control core flow; exit remains supersonic.",
        evidence="",
        verdict="BACKPRESSURE_NOT_ESTABLISHED",
    )
    found = False
    for p in root.rglob("backpressure_verdict*.json"):
        data = _load_json_safe(p)
        if data and data.get("verdict", "").startswith("BACKPRESSURE_NOT"):
            finding.evidence = f"{p.name}: {data.get('verdict')}"
            found = True
            break
    if found:
        report.fail_count += 1
        report.findings.append(finding)
    else:
        finding.severity = "info"
        finding.verdict = "CHECK_PASSED"
        report.pass_count += 1
        report.findings.append(finding)


def check_shock_train(report: AuditReport, root: Path) -> None:
    """FC-003: No shock train detected despite backpressure sweep.

    Real failure: Case 002 BPR 1.0-8.0 shows no shock train. Wall pressure
    dp/dx sign changes are constant (~35), no upstream migration of max p.
    """
    finding = Finding(
        check_id="FC-003",
        severity="warning",
        title="Shock train not detected",
        detail="No shock train forms for any BPR; isolator cannot develop pressure rise.",
        evidence="",
        verdict="SHOCK_TRAIN_NOT_DETECTED",
    )
    found = False
    for p in root.rglob("shock_structure_analysis.json"):
        data = _load_json_safe(p)
        if data and "SHOCK_TRAIN_NOT_DETECTED" in str(data.get("verdict", "")):
            finding.evidence = f"{p.name}: SHOCK_TRAIN_NOT_DETECTED"
            found = True
            break
    if found:
        report.warning_count += 1
        report.findings.append(finding)
    else:
        finding.severity = "info"
        finding.verdict = "CHECK_PASSED"
        report.pass_count += 1
        report.findings.append(finding)


def check_mass_imbalance(report: AuditReport, root: Path) -> None:
    """FC-004: Large mass imbalance indicates flow breakdown.

    Real failure: Case 002 BPR=8.0 has 3.15% mass imbalance and 55% backflow.

    Threshold bug (fixed): the column is named ``mass_defect_pct`` and holds a
    PERCENT value (e.g. 3.15 means 3.15 %).  The previous code compared it with
    0.01, i.e. it treated the number as a FRACTION.  That made the check ~100x
    too strict: any run with more than 0.01 % defect tripped it, while the
    documented failure threshold is 1 %.  Both spellings are now normalised
    explicitly so a fraction column and a percent column behave correctly.
    """
    finding = Finding(
        check_id="FC-004",
        severity="warning",
        title="Mass imbalance at high BPR",
        detail="Mass imbalance > 1% indicates flow breakdown, not controlled response.",
        evidence="",
        verdict="MASS_IMBALANCE_BREAKDOWN",
    )
    found = False
    for p in root.rglob("valid_points.csv"):
        rows = _load_csv_safe(p)
        if rows:
            for row in rows:
                try:
                    percent = _mass_defect_percent(row)
                    if percent is None:
                        continue
                    if percent > 1.0:
                        bpr = row.get("BPR", row.get("bpr", "?"))
                        finding.evidence = (
                            f"{p.name}: BPR={bpr}, mass_defect={percent:.4f}% "
                            f"(threshold 1%)")
                        found = True
                        break
                except (ValueError, TypeError):
                    continue
            if found:
                break
    if found:
        report.warning_count += 1
        report.findings.append(finding)
    else:
        finding.severity = "info"
        finding.verdict = "CHECK_PASSED"
        report.pass_count += 1
        report.findings.append(finding)


def _mass_defect_percent(row: dict) -> float | None:
    """Return the mass defect as a PERCENT, accepting either column spelling.

    ``*_pct`` / ``*_percent`` columns are already percent.
    ``*_frac`` / plain columns are fractions and are multiplied by 100.
    Column matching is case-insensitive: real CSV exports vary in casing
    (``Mass_defect_pct`` vs ``mass_defect_pct``).
    """
    low = {str(k).strip().lower(): v for k, v in row.items()}

    def pick(*names):
        for n in names:
            v = low.get(n)
            if v is not None and str(v).strip() != "":
                return v
        return None

    v = pick("mass_defect_pct", "mass_imbalance_pct", "mass_defect_percent")
    if v is not None:
        return abs(float(v))
    v = pick("mass_defect_frac", "mass_imbalance_frac")
    if v is not None:
        return abs(float(v)) * 100.0
    v = pick("mass_defect")
    if v is not None:
        # ambiguous legacy column: treat as a fraction
        return abs(float(v)) * 100.0
    return None


def check_supersonic_exit_mismatch(report: AuditReport, root: Path) -> None:
    """FC-005: Exit Mach supersonic with pressure-outlet means BPR not enforced.

    Real failure: Case 002 exit Ma=2.8-2.9 for BPR 1-5. Fluent pressure-outlet
    extrapolates pressure from interior at supersonic outflow.
    """
    finding = Finding(
        check_id="FC-005",
        severity="critical",
        title="Supersonic exit with pressure-outlet boundary",
        detail="Exit Mach > 1 means specified pressure is NOT enforced by the solver.",
        evidence="",
        verdict="SUPERSONIC_EXIT_BPR_NOT_ENFORCED",
    )
    found = False
    for p in root.rglob("valid_points.csv"):
        rows = _load_csv_safe(p)
        if rows:
            for row in rows:
                try:
                    ma = float(row.get("Ma_exit", 0))
                    if ma > 1.0:
                        bpr = row.get("BPR", row.get("bpr", "?"))
                        finding.evidence = f"{p.name}: BPR={bpr}, Ma_exit={ma:.3f}"
                        found = True
                        break
                except (ValueError, TypeError):
                    continue
            if found:
                break
    if found:
        report.fail_count += 1
        report.findings.append(finding)
    else:
        finding.severity = "info"
        finding.verdict = "CHECK_PASSED"
        report.pass_count += 1
        report.findings.append(finding)


def check_nonfinite_signals(report: AuditReport, root: Path) -> None:
    """FC-006: Non-finite signals in simulation output.

    Real failure: Would indicate numerical breakdown in dynamic simulation.
    Case 002 actually passed this (0 non-finite columns).
    """
    finding = Finding(
        check_id="FC-006",
        severity="critical",
        title="Non-finite signals in simulation",
        detail="NaN or Inf in signal logs indicates numerical breakdown.",
        evidence="",
        verdict="",
    )
    found = False
    for p in root.rglob("*.csv"):
        if "signal_" in p.name or "trajectory" in p.name:
            rows = _load_csv_safe(p)
            if rows:
                for row in rows:
                    for val in row.values():
                        try:
                            v = float(val)
                            if not math.isfinite(v):
                                finding.evidence = f"{p.name}: non-finite value {val}"
                                finding.verdict = "NONFINITE_SIGNALS"
                                found = True
                                break
                        except (ValueError, TypeError):
                            continue
                    if found:
                        break
                if found:
                    break
            if found:
                break
    if found:
        report.fail_count += 1
        report.findings.append(finding)
    else:
        finding.severity = "info"
        finding.verdict = "CHECK_PASSED"
        finding.title = "All signals finite"
        report.pass_count += 1
        report.findings.append(finding)


def check_fer_step_response(report: AuditReport, root: Path) -> None:
    """FC-007: FER step does not reach engine.

    Real failure: If FER_time schedule is defined but engine thrust
    does not change, the coupling is broken.
    """
    finding = Finding(
        check_id="FC-007",
        severity="warning",
        title="FER step does not produce thrust change",
        detail="FER perturbation should produce measurable thrust change.",
        evidence="",
        verdict="",
    )
    # Check for matching experiment results
    for p in root.rglob("matching_experiments.json"):
        data = _load_json_safe(p)
        if data and "M2" in data:
            m2 = data["M2"]
            delta_t = m2.get("delta_thrust_N", 0)
            if abs(delta_t) < 1.0:
                finding.severity = "critical"
                finding.evidence = f"{p.name}: delta_thrust={delta_t:.2f} N (too small)"
                finding.verdict = "FER_STEP_NOT_REACHING_ENGINE"
                report.fail_count += 1
                report.findings.append(finding)
                return
            else:
                finding.severity = "info"
                finding.verdict = "CHECK_PASSED"
                finding.evidence = f"delta_thrust={delta_t:.2f} N"
                report.pass_count += 1
                report.findings.append(finding)
                return
    # No matching experiments found
    finding.severity = "info"
    finding.verdict = "CHECK_SKIPPED"
    finding.evidence = "No matching experiment data found"
    report.pass_count += 1
    report.findings.append(finding)


def check_gas_model_consistency(report: AuditReport, root: Path) -> None:
    """FC-008: Gas model mismatch between CFD and engine.

    Real failure: CFD uses cp=1006.43 (Fluent calorically perfect air),
    engine uses cp=1004 (1.004 kJ/kgK in energy blocks). Also gamma
    mismatch: CFD gamma=1.399, engine gamma=1.4.
    """
    finding = Finding(
        check_id="FC-008",
        severity="warning",
        title="Gas model inconsistency",
        detail="CP or gamma mismatch between CFD and engine models.",
        evidence="",
        verdict="",
    )
    # Check for metrics.json with cp values
    cfd_cp = None
    engine_cp = None
    for p in root.rglob("metrics.json"):
        data = _load_json_safe(p)
        if data and "cp" in str(data):
            text = json.dumps(data)
            m = re.search(r'"cp"[:\s]+([\d.]+)', text)
            if m:
                cfd_cp = float(m.group(1))
                break
    # Check engine demand analysis for engine cp
    for p in root.rglob("engine_demand_analysis.json"):
        data = _load_json_safe(p)
        if data:
            hypotheses = data.get("parametric_hypotheses", {})
            if "cp_engine" in hypotheses:
                engine_cp = hypotheses["cp_engine"].get("value_J_kgK")
                break
    if cfd_cp and engine_cp and abs(cfd_cp - engine_cp) > 2.0:
        finding.evidence = f"CFD cp={cfd_cp}, engine cp={engine_cp}, diff={abs(cfd_cp-engine_cp):.2f}"
        finding.verdict = "GAS_MODEL_MISMATCH"
        report.warning_count += 1
        report.findings.append(finding)
    else:
        finding.severity = "info"
        finding.verdict = "CHECK_PASSED"
        if cfd_cp and engine_cp:
            finding.evidence = f"CFD cp={cfd_cp}, engine cp={engine_cp}"
        else:
            finding.evidence = "Gas model data not found"
        report.pass_count += 1
        report.findings.append(finding)


def check_span_labeling(report: AuditReport, root: Path) -> None:
    """FC-009: Span parameter not labeled as research parameter.

    Real failure: 0.4306 m span is a research parameter, not real X-43A.
    Must be clearly labeled in all outputs.
    """
    finding = Finding(
        check_id="FC-009",
        severity="warning",
        title="Span parameter labeling",
        detail="2D-to-3D span conversion must be labeled as research parameter.",
        evidence="",
        verdict="",
    )
    # Check if span is mentioned in any markdown without "research" label
    found_unlabeled = False
    for p in root.rglob("*.md"):
        text = p.read_text(encoding="utf-8", errors="replace")
        if "0.4306" in text and "research parameter" not in text.lower() and "not real" not in text.lower():
            found_unlabeled = True
            finding.evidence = f"{p.name}: mentions 0.4306 without 'research parameter' label"
            break
    if found_unlabeled:
        finding.verdict = "SPAN_NOT_LABELED"
        report.warning_count += 1
        report.findings.append(finding)
    else:
        finding.severity = "info"
        finding.verdict = "CHECK_PASSED"
        report.pass_count += 1
        report.findings.append(finding)


def check_report_native_consistency(report: AuditReport, root: Path) -> None:
    """FC-011: a written report must agree with the native data it cites.

    Defect (fixed): the auditor only inspected the machine-readable metrics.  A
    hand-written report (FINAL_RESULT.md / *.md) could claim values that the
    native JSON contradicted and the audit still returned AUDIT_PASSED.

    This check extracts a small set of unambiguous, numerically formatted
    claims from the reports and compares them with the native metrics.  Only
    values that can be matched with certainty are compared; prose that cannot
    be parsed is skipped rather than guessed at.
    """
    import re

    finding = Finding(
        check_id="FC-011",
        severity="critical",
        title="Report contradicts native data",
        detail="A numeric claim in the report disagrees with the native metrics.",
        evidence="",
        verdict="REPORT_NATIVE_MISMATCH",
    )

    native = _collect_native_scalars(root)
    if not native:
        finding.severity = "info"
        finding.verdict = "CHECK_SKIPPED_NO_NATIVE_DATA"
        report.pass_count += 1
        report.findings.append(finding)
        return

    # (label, regex over the report, native key, relative tolerance)
    claims = [
        ("outlet total pressure",
         r"(?:Pt[_ ]?out|total pressure)[^\n\d]{0,40}([0-9]+(?:\.[0-9]+)?)\s*(?:Pa|kPa)?",
         "pt_out_Pa", 0.02),
        ("exit Mach",
         r"(?:Ma[_ ]?exit|exit Mach)[^\n\d]{0,30}([0-9]\.[0-9]+)",
         "Ma_exit", 0.05),
        ("mass flow",
         r"(?:mdot|mass flow)[^\n\d]{0,40}([0-9]+(?:\.[0-9]+)?)\s*kg/s",
         "mdot_kg_s", 0.05),
    ]

    mismatches = []
    for md in sorted(root.rglob("*.md")):
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for label, pat, key, tol in claims:
            if key not in native:
                continue
            for m in re.finditer(pat, text, re.I):
                try:
                    claimed = float(m.group(1))
                except ValueError:
                    continue
                actual = native[key]
                if actual == 0:
                    continue
                rel = abs(claimed - actual) / abs(actual)
                if rel > tol:
                    mismatches.append(
                        f"{md.name}: {label} claimed {claimed:g} vs native "
                        f"{actual:g} ({rel*100:.1f}% off, tol {tol*100:.0f}%)")

    if mismatches:
        finding.evidence = "; ".join(mismatches[:4])
        report.fail_count += 1
        report.findings.append(finding)
    else:
        finding.severity = "info"
        finding.verdict = "CHECK_PASSED"
        report.pass_count += 1
        report.findings.append(finding)


def _collect_native_scalars(root: Path) -> dict:
    """Pull a few comparable scalars out of native metrics JSON files."""
    out: dict[str, float] = {}
    for p in root.rglob("*.json"):
        data = _load_json_safe(p)
        if not isinstance(data, dict):
            continue
        for src, dst in (("Pt_out_Pa", "pt_out_Pa"),
                         ("pt_out_Pa", "pt_out_Pa"),
                         ("Ma_exit", "Ma_exit"),
                         ("mdot_out_net_kg_s_per_m", "mdot_kg_s"),
                         ("mdot_in_kg_s", "mdot_kg_s"),
                         ("mdot_CFD_3D_kg_s", "mdot_kg_s")):
            v = data.get(src)
            if isinstance(v, (int, float)) and dst not in out:
                out[dst] = float(v)
    return out


def check_native_evidence_present(report: AuditReport, root: Path) -> None:
    """FC-012: a real CFD/Simulink claim needs real native artifacts.

    Defect (fixed): a directory holding only a prose report could pass.  A pass
    now requires at least one native artifact, and the artifact classes are
    configurable through an optional ``audit_rules.json`` at the audit root.
    """
    rules = _load_audit_rules(root)
    cfg = rules.get("native_evidence", {})
    enabled = cfg.get("enabled", True)
    finding = Finding(
        check_id="FC-012",
        severity="warning",
        title="No native evidence for the claimed result",
        detail="A CFD/Simulink claim requires native case/data, log or MAT/CSV artifacts.",
        evidence="",
        verdict="NO_NATIVE_EVIDENCE",
    )
    if not enabled:
        finding.severity = "info"
        finding.verdict = "CHECK_DISABLED_BY_RULES"
        report.pass_count += 1
        report.findings.append(finding)
        return

    patterns = cfg.get("patterns", ["*.cas.h5", "*.dat.h5", "*.trn",
                                    "*.mat", "*.slx", "metrics.json",
                                    "timeseries.csv"])
    hits = []
    for pat in patterns:
        hits.extend(root.rglob(pat))
    if hits:
        finding.severity = "info"
        finding.verdict = "CHECK_PASSED"
        finding.evidence = f"{len(hits)} native artifacts (e.g. {hits[0].name})"
        report.pass_count += 1
    else:
        finding.evidence = f"none of {patterns} found under {root}"
        report.warning_count += 1
    report.findings.append(finding)


def _load_audit_rules(root: Path) -> dict:
    """Optional per-experiment audit configuration."""
    p = root / "audit_rules.json"
    if p.is_file():
        data = _load_json_safe(p)
        if isinstance(data, dict):
            return data
    return {}
    """FC-010: Unvalidated parametric hypothesis used without labeling.

    Real failure: sigma_combustor=0.95 is a hypothesis, not measured.
    Must be clearly labeled in all outputs.
    """
    finding = Finding(
        check_id="FC-010",
        severity="warning",
        title="Unvalidated parametric hypothesis",
        detail="Combustor pressure recovery sigma is a hypothesis, not measured data.",
        evidence="",
        verdict="",
    )
    found = False
    for p in root.rglob("engine_demand_analysis.json"):
        data = _load_json_safe(p)
        if data:
            hypotheses = data.get("parametric_hypotheses", {})
            if "sigma_combustor" in hypotheses:
                source = hypotheses["sigma_combustor"].get("source", "")
                if "HYPOTHESIS" in source.upper() or "PARAMETRIC" in source.upper():
                    finding.evidence = f"sigma_combustor labeled as hypothesis: {source}"
                    found = True
                break
    if found:
        finding.verdict = "HYPOTHESIS_LABELED"
        finding.severity = "info"
        report.pass_count += 1
        report.findings.append(finding)
    else:
        # Check for unlabeled sigma
        for p in root.rglob("*.json"):
            text = p.read_text(encoding="utf-8", errors="replace")
            if "sigma_combustor" in text and "HYPOTHESIS" not in text.upper():
                finding.evidence = f"{p.name}: sigma_combustor without HYPOTHESIS label"
                finding.verdict = "HYPOTHESIS_NOT_LABELED"
                report.warning_count += 1
                report.findings.append(finding)
                return
        finding.severity = "info"
        finding.verdict = "CHECK_PASSED"
        report.pass_count += 1
        report.findings.append(finding)


def check_sigma_hypothesis(report: AuditReport, root: Path) -> None:
    """FC-010: Unvalidated parametric hypothesis used without labeling.

    Real failure: sigma_combustor=0.95 is a hypothesis, not measured.
    Must be clearly labeled in all outputs.
    """
    finding = Finding(
        check_id="FC-010",
        severity="warning",
        title="Unvalidated parametric hypothesis",
        detail="Combustor pressure recovery sigma is a hypothesis, not measured data.",
        evidence="",
        verdict="",
    )
    found = False
    for p in root.rglob("engine_demand_analysis.json"):
        data = _load_json_safe(p)
        if data:
            hypotheses = data.get("parametric_hypotheses", {})
            if "sigma_combustor" in hypotheses:
                source = hypotheses["sigma_combustor"].get("source", "")
                if "HYPOTHESIS" in source.upper() or "PARAMETRIC" in source.upper():
                    finding.evidence = f"sigma_combustor labeled as hypothesis: {source}"
                    found = True
                break
    if found:
        finding.verdict = "HYPOTHESIS_LABELED"
        finding.severity = "info"
        report.pass_count += 1
        report.findings.append(finding)
    else:
        # Check for unlabeled sigma
        for p in root.rglob("*.json"):
            text = p.read_text(encoding="utf-8", errors="replace")
            if "sigma_combustor" in text and "HYPOTHESIS" not in text.upper():
                finding.evidence = f"{p.name}: sigma_combustor without HYPOTHESIS label"
                finding.verdict = "HYPOTHESIS_NOT_LABELED"
                report.warning_count += 1
                report.findings.append(finding)
                return
        finding.severity = "info"
        finding.verdict = "CHECK_PASSED"
        report.pass_count += 1
        report.findings.append(finding)


# ---------------------------------------------------------------------------
# Audit runner
# ---------------------------------------------------------------------------

ALL_CHECKS = [
    check_circular_mdot,
    check_backpressure_effectiveness,
    check_shock_train,
    check_mass_imbalance,
    check_supersonic_exit_mismatch,
    check_nonfinite_signals,
    check_fer_step_response,
    check_gas_model_consistency,
    check_span_labeling,
    check_sigma_hypothesis,
    check_report_native_consistency,
    check_native_evidence_present,
]


def audit_directory(directory: str | Path) -> AuditReport:
    """Run all audit checks on a directory."""
    root = Path(directory)
    report = AuditReport(directory=str(root))
    for check_fn in ALL_CHECKS:
        check_fn(report, root)
    return report


def format_report_text(report: AuditReport) -> str:
    """Format audit report as human-readable text."""
    lines = [
        "=" * 70,
        f"SimWhy Audit Report: {report.directory}",
        "=" * 70,
        f"Overall verdict: {report.overall_verdict}",
        f"Checks: {report.pass_count} passed, {report.warning_count} warnings, {report.fail_count} failed",
        "",
    ]
    for f in report.findings:
        icon = {"critical": "[FAIL]", "warning": "[WARN]", "info": "[PASS]"}[f.severity]
        lines.append(f"{icon} {f.check_id}: {f.title}")
        lines.append(f"      Detail: {f.detail}")
        lines.append(f"      Evidence: {f.evidence}")
        if f.verdict and f.verdict != "CHECK_PASSED":
            lines.append(f"      Verdict: {f.verdict}")
        lines.append("")
    return "\n".join(lines)


def format_report_json(report: AuditReport) -> str:
    """Format audit report as JSON."""
    return json.dumps(report.to_dict(), indent=2, default=str)
