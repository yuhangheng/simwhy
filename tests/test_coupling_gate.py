"""Synthetic-only unit tests: absence of evidence must NEVER validate coupling."""
import unittest

from simwhy.coupling_gate import assess_backpressure, assess_pressure_ablation, assess_evidence


def case(pb, upstream, drift=5.0, balance=0.2, geometry="G"):
    return {"geometry_id": geometry, "backpressure_pa": pb,
            "upstream_pressure_pa": upstream, "iteration_drift_pa": drift,
            "mass_imbalance_pct": balance}


def traces(offset_inlet=0.0, offset_thrust=0.0):
    a = {"time_s": [0, 0.1, 0.2],
         "pressure_command_pa": [10000, 12000, 14000],
         "inlet_pressure_pa": [30000+offset_inlet, 30010+offset_inlet, 30020+offset_inlet],
         "thrust_n": [1000+offset_thrust, 1001+offset_thrust, 1002+offset_thrust]}
    b = {"time_s": [0, 0.1, 0.2],
         "pressure_command_pa": [10000, 12000, 14000],
         "inlet_pressure_pa": [30000, 30010, 30020],
         "thrust_n": [1000, 1001, 1002]}
    return a, b


class TestFixedGeometry(unittest.TestCase):
    def test_no_pressure_dimension_is_not_valid(self):
        r=assess_backpressure([case(10000,20000),case(10000,22000,geometry="H")])
        self.assertEqual(r["status"],"INSUFFICIENT_FIXED_GEOMETRY_SWEEP")

    def test_outlet_change_but_no_upstream_response(self):
        r=assess_backpressure([case(10000,20000),case(14000,20000.01)])
        self.assertEqual(r["status"],"NO_RESOLVED_UPSTREAM_RESPONSE")

    def test_large_change_but_mass_imbalance_unreliable(self):
        r=assess_backpressure([case(10000,20000,balance=0.2),case(14000,20500,balance=3.0)])
        self.assertEqual(r["status"],"RESPONSE_WITH_UNACCEPTABLE_BALANCE")

    def test_resolved_response_only_numerical(self):
        r=assess_backpressure([case(10000,20000),case(14000,20100)])
        self.assertEqual(r["status"],"RESOLVED_NUMERIC_UPSTREAM_RESPONSE")
        self.assertTrue(r["pairs"][0]["usable_numeric_pair"])

    def test_missing_drift_is_not_silent_success(self):
        d=case(10000,20000); del d["iteration_drift_pa"]
        with self.assertRaises(ValueError):
            assess_backpressure([d])

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            assess_backpressure([case(10000,float("nan"))])


class TestAblation(unittest.TestCase):
    def test_zero_pressure_feedback_does_nothing(self):
        self.assertEqual(assess_pressure_ablation(*traces())["status"],
                         "PRESSURE_FEEDBACK_NO_MEASURABLE_EFFECT")

    def test_nonzero_numeric_effect_not_physical_proof(self):
        self.assertEqual(assess_pressure_ablation(*traces(10,2))["status"],
                         "NUMERICALLY_SENSITIVE_NOT_PHYSICALLY_VALIDATED")

    def test_inlet_only_not_enough(self):
        self.assertEqual(assess_pressure_ablation(*traces(10,0))["status"],
                         "PARTIAL_NUMERIC_SENSITIVITY")

    def test_no_command_excitation_is_inconclusive(self):
        a,b=traces(10,2)
        a["pressure_command_pa"]=[10000]*3
        b["pressure_command_pa"]=[10000]*3
        self.assertEqual(assess_pressure_ablation(a,b)["status"],"NO_PRESSURE_EXCITATION")

    def test_mismatched_time_rejected(self):
        a,b=traces(10,2)
        b["time_s"]=[0,0.15,0.2]
        with self.assertRaises(ValueError):
            assess_pressure_ablation(a,b)


class TestOverall(unittest.TestCase):
    def test_empty_file_not_validated(self):
        self.assertEqual(assess_evidence({})["verdict"],"PHYSICAL_COUPLING_NOT_VALIDATED")

    def test_even_numeric_sensitivity_is_not_physical_certification(self):
        a,b=traces(10,2)
        r=assess_evidence({"cfd_cases":[case(10000,20000),case(14000,20100)],
                           "pressure_ablation":{"nominal":a,"pressure_off":b}})
        self.assertEqual(r["verdict"],"NUMERICALLY_SUPPORTED_REQUIRES_PHYSICAL_VALIDATION")


if __name__=="__main__":
    unittest.main()
