"""Executable regression tests for the SimWhy Audit engine.

Each test constructs a minimal synthetic case directory demonstrating one
specific failure pattern (or its absence) and asserts the audit verdict.

Run: python -m unittest discover -s tests -v
"""
import json
import math
import shutil
import unittest
from pathlib import Path

from simwhy.audit import audit_directory, AuditReport, Finding

# Use a predictable writable workspace instead of tempfile (the Windows sandbox
# denies writes inside tempfile-created directories in this environment).
_WORKSPACE = Path(__file__).resolve().parent / "_audit_scratch"


def _touch(path: Path, content: str = ""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class AuditTestCase(unittest.TestCase):
    def setUp(self):
        self._roots = []
        _WORKSPACE.mkdir(parents=True, exist_ok=True)

    def _make_dir(self) -> Path:
        # deterministic per-test directory
        name = f"case_{len(self._roots)}"
        root = _WORKSPACE / name
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)
        self._roots.append(root)
        return root

    def _run(self, root: Path, check_id: str) -> Finding:
        report = audit_directory(root)
        for f in report.findings:
            if f.check_id == check_id:
                return f
        raise AssertionError(f"{check_id} not executed")

    def tearDown(self):
        for r in self._roots:
            if r.exists():
                shutil.rmtree(r, ignore_errors=True)


# ---------------------------------------------------------------------------
# Failure-case tests (each demonstrates one real failure pattern)
# ---------------------------------------------------------------------------

class TestFC001CircularMdot(AuditTestCase):
    def test_detects_circular_mdot(self):
        root = self._make_dir()
        _touch(root / "engine_demand_analysis.json",
               json.dumps({"circular_definition_check": {"existing_engine_receives_mdot": True}}))
        f = self._run(root, "FC-001")
        self.assertEqual(f.severity, "critical")
        self.assertIn("NOT_INDEPENDENT", f.verdict)

    def test_passes_when_absent(self):
        root = self._make_dir()
        f = self._run(root, "FC-001")
        self.assertEqual(f.severity, "info")
        self.assertEqual(f.verdict, "CHECK_PASSED")


class TestFC002Backpressure(AuditTestCase):
    def test_detects_backpressure_not_established(self):
        root = self._make_dir()
        _touch(root / "backpressure_verdict_refined.json",
               json.dumps({"verdict": "BACKPRESSURE_NOT_ESTABLISHED"}))
        f = self._run(root, "FC-002")
        self.assertEqual(f.severity, "critical")
        self.assertIn("NOT_ESTABLISHED", f.verdict)

    def test_passes_when_established(self):
        root = self._make_dir()
        _touch(root / "backpressure_verdict.json",
               json.dumps({"verdict": "BACKPRESSURE_PHYSICALLY_EFFECTIVE"}))
        f = self._run(root, "FC-002")
        self.assertEqual(f.severity, "info")
        self.assertEqual(f.verdict, "CHECK_PASSED")


class TestFC003ShockTrain(AuditTestCase):
    def test_detects_no_shock_train(self):
        root = self._make_dir()
        _touch(root / "shock_structure_analysis.json",
               json.dumps({"verdict": "SHOCK_TRAIN_NOT_DETECTED"}))
        f = self._run(root, "FC-003")
        self.assertEqual(f.severity, "warning")
        self.assertIn("NOT_DETECTED", f.verdict)

    def test_passes_when_detected(self):
        root = self._make_dir()
        _touch(root / "shock_structure_analysis.json",
               json.dumps({"verdict": "SHOCK_TRAIN_DETECTED_AT_BPR_6"}))
        f = self._run(root, "FC-003")
        self.assertEqual(f.severity, "info")
        self.assertEqual(f.verdict, "CHECK_PASSED")


class TestFC004MassImbalance(AuditTestCase):
    def test_detects_mass_imbalance(self):
        root = self._make_dir()
        header = "case_id,bpr,mass_defect_pct\n"
        row = "M400_A000_B800,8.0,3.1478\n"
        _touch(root / "valid_points.csv", header + row)
        f = self._run(root, "FC-004")
        self.assertEqual(f.severity, "warning")
        self.assertIn("BREAKDOWN", f.verdict)

    def test_passes_when_balanced(self):
        root = self._make_dir()
        header = "case_id,bpr,mass_defect_pct\n"
        row = "M400_A000_B100,1.0,0.005\n"
        _touch(root / "valid_points.csv", header + row)
        f = self._run(root, "FC-004")
        self.assertEqual(f.severity, "info")
        self.assertEqual(f.verdict, "CHECK_PASSED")


class TestFC005SupersonicExit(AuditTestCase):
    def test_detects_supersonic_exit(self):
        root = self._make_dir()
        header = "case_id,bpr,Ma_exit\n"
        row = "M400_A000_B100,1.0,2.862\n"
        _touch(root / "valid_points.csv", header + row)
        f = self._run(root, "FC-005")
        self.assertEqual(f.severity, "critical")
        self.assertIn("NOT_ENFORCED", f.verdict)

    def test_passes_when_subsonic(self):
        root = self._make_dir()
        header = "case_id,bpr,Ma_exit\n"
        row = "M400_A000_B100,1.0,0.45\n"
        _touch(root / "valid_points.csv", header + row)
        f = self._run(root, "FC-005")
        self.assertEqual(f.severity, "info")
        self.assertEqual(f.verdict, "CHECK_PASSED")


class TestFC006Nonfinite(AuditTestCase):
    def test_detects_nonfinite(self):
        root = self._make_dir()
        header = "time_s,thrust_n\n"
        row = "0.0,NaN\n"
        _touch(root / "trajectory.csv", header + row)
        f = self._run(root, "FC-006")
        self.assertEqual(f.severity, "critical")
        self.assertIn("NONFINITE", f.verdict)

    def test_passes_when_finite(self):
        root = self._make_dir()
        header = "time_s,thrust_n\n"
        row = "0.0,3628.75\n"
        _touch(root / "trajectory.csv", header + row)
        f = self._run(root, "FC-006")
        self.assertEqual(f.severity, "info")
        self.assertEqual(f.verdict, "CHECK_PASSED")


class TestFC007FerStep(AuditTestCase):
    def test_detects_no_fer_response(self):
        root = self._make_dir()
        _touch(root / "matching_experiments.json",
               json.dumps({"M2": {"delta_thrust_N": 0.12}}))
        f = self._run(root, "FC-007")
        self.assertEqual(f.severity, "critical")
        self.assertIn("NOT_REACHING_ENGINE", f.verdict)

    def test_passes_with_response(self):
        root = self._make_dir()
        _touch(root / "matching_experiments.json",
               json.dumps({"M2": {"delta_thrust_N": 64.63}}))
        f = self._run(root, "FC-007")
        self.assertEqual(f.severity, "info")
        self.assertEqual(f.verdict, "CHECK_PASSED")


class TestFC008GasModel(AuditTestCase):
    def test_detects_gas_model_mismatch(self):
        root = self._make_dir()
        _touch(root / "metrics.json", json.dumps({"fluid": {"cp": 1006.43}}))
        _touch(root / "engine_demand_analysis.json",
               json.dumps({"parametric_hypotheses": {"cp_engine": {"value_J_kgK": 1004.0}}}))
        f = self._run(root, "FC-008")
        self.assertEqual(f.severity, "warning")
        self.assertIn("MISMATCH", f.verdict)

    def test_passes_when_consistent(self):
        root = self._make_dir()
        _touch(root / "metrics.json", json.dumps({"fluid": {"cp": 1004.0}}))
        _touch(root / "engine_demand_analysis.json",
               json.dumps({"parametric_hypotheses": {"cp_engine": {"value_J_kgK": 1004.0}}}))
        f = self._run(root, "FC-008")
        self.assertEqual(f.severity, "info")
        self.assertEqual(f.verdict, "CHECK_PASSED")


class TestFC009SpanLabeling(AuditTestCase):
    def test_warns_when_unlabeled(self):
        root = self._make_dir()
        _touch(root / "report.md", "We used a span of 0.4306 m for the 3D conversion.")
        f = self._run(root, "FC-009")
        self.assertEqual(f.severity, "warning")
        self.assertIn("NOT_LABELED", f.verdict)

    def test_passes_when_labeled(self):
        root = self._make_dir()
        _touch(root / "report.md", "span=0.4306 m (research parameter, not real X-43A)")
        f = self._run(root, "FC-009")
        self.assertEqual(f.severity, "info")
        self.assertEqual(f.verdict, "CHECK_PASSED")


class TestFC010Hypothesis(AuditTestCase):
    def test_passes_when_labeled(self):
        root = self._make_dir()
        _touch(root / "engine_demand_analysis.json",
               json.dumps({"parametric_hypotheses":
                           {"sigma_combustor": {"source": "PARAMETRIC HYPOTHESIS - no public data"}}}))
        f = self._run(root, "FC-010")
        self.assertEqual(f.severity, "info")
        self.assertEqual(f.verdict, "HYPOTHESIS_LABELED")

    def test_warns_when_unlabeled(self):
        root = self._make_dir()
        _touch(root / "engine_demand_analysis.json",
               json.dumps({"parametric_hypotheses":
                           {"sigma_combustor": {"source": "combustor recovery"}}}))
        f = self._run(root, "FC-010")
        self.assertEqual(f.severity, "warning")
        self.assertIn("NOT_LABELED", f.verdict)


class TestAuditAggregation(AuditTestCase):
    """End-to-end: a directory with multiple failures must report AUDIT_FAILED."""
    def test_overall_failed(self):
        root = self._make_dir()
        _touch(root / "backpressure_verdict.json",
               json.dumps({"verdict": "BACKPRESSURE_NOT_ESTABLISHED"}))
        _touch(root / "valid_points.csv", "case_id,bpr,Ma_exit\nM400_A000_B100,1.0,2.9\n")
        report = audit_directory(root)
        self.assertEqual(report.overall_verdict, "AUDIT_FAILED")
        self.assertGreater(report.fail_count, 0)

    def test_overall_passed(self):
        root = self._make_dir()
        # A directory with real native evidence and no failure pattern must
        # pass.  An EMPTY directory must not (see the test below): a pass has
        # to be earned by at least one native artifact.
        _touch(root / "cfd" / "run.cas.h5", "native case")
        _touch(root / "cfd" / "run.dat.h5", "native data")
        report = audit_directory(root)
        self.assertEqual(report.overall_verdict, "AUDIT_PASSED")
        self.assertEqual(report.fail_count, 0)

    def test_empty_directory_is_not_a_pass(self):
        """Regression: an empty experiment directory must never pass.

        The previous auditor returned AUDIT_PASSED for a directory containing
        nothing at all, because every check degraded to 'skip' and no check
        ever failed.  'Nothing verified' is not 'verified nothing wrong'.
        """
        root = self._make_dir()
        report = audit_directory(root)
        self.assertNotEqual(report.overall_verdict, "AUDIT_PASSED")
        ids = {f.check_id for f in report.findings}
        self.assertIn("FC-012", ids)


class TestRegressionFixes(AuditTestCase):
    """Counter-example tests for the four defects this branch fixes."""

    # ---- FC-004: percent vs fraction -----------------------------------
    def test_fc004_percent_column_below_threshold_passes(self):
        """0.5 % defect is BELOW the 1 % threshold and must not trip FC-004.

        The old code compared the percent value against 0.01, so 0.5 was read
        as 50 % and every normal run was flagged.
        """
        root = self._make_dir()
        _touch(root / "valid_points.csv",
               "case_id,bpr,Mass_defect_pct\nA,1.0,0.5\n")
        f = self._run(root, "FC-004")
        self.assertEqual(f.verdict, "CHECK_PASSED")

    def test_fc004_percent_column_above_threshold_fails(self):
        root = self._make_dir()
        _touch(root / "valid_points.csv",
               "case_id,bpr,Mass_defect_pct\nA,8.0,3.15\n")
        f = self._run(root, "FC-004")
        self.assertEqual(f.verdict, "MASS_IMBALANCE_BREAKDOWN")

    def test_fc004_fraction_column_is_converted(self):
        """A fraction column (0.0315 = 3.15 %) must also be understood."""
        root = self._make_dir()
        _touch(root / "valid_points.csv",
               "case_id,bpr,mass_defect_frac\nA,8.0,0.0315\n")
        f = self._run(root, "FC-004")
        self.assertEqual(f.verdict, "MASS_IMBALANCE_BREAKDOWN")

    # ---- empty directory ------------------------------------------------
    def test_empty_dir_is_inconclusive_not_passed(self):
        root = self._make_dir()
        report = audit_directory(root)
        self.assertNotEqual(report.overall_verdict, "AUDIT_PASSED")

    # ---- report vs native data -----------------------------------------
    def test_report_contradicting_native_data_fails(self):
        """A report claiming a different Pt_out than the native metric fails."""
        root = self._make_dir()
        _touch(root / "cfd" / "run.cas.h5", "native")
        _touch(root / "cfd" / "metrics.json",
               json.dumps({"Pt_out_Pa": 412427.78, "Ma_exit": 2.216}))
        _touch(root / "FINAL_RESULT.md",
               "The outlet total pressure was 300000 Pa at the exit.\n")
        report = audit_directory(root)
        self.assertEqual(report.overall_verdict, "AUDIT_FAILED")
        ids = {f.check_id for f in report.findings}
        self.assertIn("FC-011", ids)

    def test_report_agreeing_with_native_data_passes(self):
        root = self._make_dir()
        _touch(root / "cfd" / "run.cas.h5", "native")
        _touch(root / "cfd" / "metrics.json",
               json.dumps({"Pt_out_Pa": 412427.78, "Ma_exit": 2.216}))
        _touch(root / "FINAL_RESULT.md",
               "The outlet total pressure was 412427.78 Pa.\n")
        report = audit_directory(root)
        f = [x for x in report.findings if x.check_id == "FC-011"][0]
        self.assertEqual(f.verdict, "CHECK_PASSED")

    # ---- native evidence requirement ------------------------------------
    def test_missing_native_evidence_warns(self):
        root = self._make_dir()
        _touch(root / "report.md", "some prose only\n")
        f = self._run(root, "FC-012")
        self.assertEqual(f.verdict, "NO_NATIVE_EVIDENCE")

    def test_native_evidence_satisfied(self):
        root = self._make_dir()
        _touch(root / "cfd" / "run.cas.h5", "native")
        f = self._run(root, "FC-012")
        self.assertEqual(f.verdict, "CHECK_PASSED")

    def test_native_evidence_rule_is_configurable(self):
        """audit_rules.json can disable the evidence requirement."""
        root = self._make_dir()
        _touch(root / "audit_rules.json",
               json.dumps({"native_evidence": {"enabled": False}}))
        f = self._run(root, "FC-012")
        self.assertEqual(f.verdict, "CHECK_DISABLED_BY_RULES")

    def test_custom_evidence_pattern_is_honoured(self):
        root = self._make_dir()
        _touch(root / "audit_rules.json",
               json.dumps({"native_evidence": {"patterns": ["*.slx"]}}))
        _touch(root / "model.slx", "native")
        f = self._run(root, "FC-012")
        self.assertEqual(f.verdict, "CHECK_PASSED")


if __name__ == "__main__":
    unittest.main()
