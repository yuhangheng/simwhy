"""Executable unit/invariant/CLI tests; run: python -m unittest discover -s tests -v."""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from simwhy.core import Config, simulate, nozzle_flow, step_refinement


class PhysicsTests(unittest.TestCase):
    def test_validation_unknown_and_bad_values(self):
        for config in ({"watts": 10}, {"gamma": 1.0}, {"tank_volume_m3": 0},
                       {"discharge_coefficient": 1.5}, {"tank_pressure_pa": 101325}):
            with self.assertRaises(ValueError):
                Config.from_dict(config)

    def test_choked_flow_matches_critical_ratio(self):
        c = Config()
        mdot, thrust, choked = nozzle_flow(c.tank_pressure_pa, c.tank_temperature_k, c)
        self.assertTrue(choked)
        self.assertGreater(thrust, mdot * math.sqrt(c.gamma * c.gas_constant_j_per_kg_k
                                                   * c.tank_temperature_k * 2/(c.gamma+1)))
        self.assertGreater(mdot, 0)

    def test_zero_differential_pressure(self):
        c = Config()
        self.assertEqual(nozzle_flow(c.ambient_pressure_pa, 300.0, c), (0.0, 0.0, False))

    def test_un_choked_flow_is_positive(self):
        c = Config(tank_pressure_pa=120000.0)
        mdot, force, choked = nozzle_flow(c.tank_pressure_pa, c.tank_temperature_k, c)
        self.assertFalse(choked)
        self.assertGreater(mdot, 0)
        self.assertGreater(force, 0)

    def test_tank_mass_and_monotonicity(self):
        c = Config()
        rows, summary = simulate(c)
        self.assertAlmostEqual(summary["gas_consumed_kg"],
                               summary["initial_gas_kg"]-summary["gas_left_kg"], places=9)
        self.assertLess(summary["numerical_mass_balance_error_kg"], 1e-9)
        self.assertTrue(all(a["tank_pressure_pa"] >= b["tank_pressure_pa"] - 1e-6
                            for a, b in zip(rows, rows[1:])))
        self.assertTrue(all(a["altitude_m"] >= 0 for a in rows))
        self.assertTrue(all(math.isfinite(r["thrust_n"]) for r in rows))
        self.assertGreater(summary["peak_altitude_m"], 0)

    def test_no_actuation_no_jump(self):
        c = Config(valve_open_s=0.0)
        rows, summary = simulate(c)
        self.assertEqual(summary["peak_altitude_m"], 0)
        self.assertEqual(summary["gas_consumed_kg"], 0)
        self.assertTrue(all(r["vertical_velocity_mps"] == 0 for r in rows))

    def test_weak_jet_cannot_lift(self):
        c = Config.from_dict(json.loads(Path("examples/insufficient_thrust.json").read_text()))
        _, summary = simulate(c)
        self.assertLess(summary["initial_thrust_to_weight"], 1)
        self.assertEqual(summary["peak_altitude_m"], 0)

    def test_time_step_sensitivity(self):
        study = step_refinement(Config())
        self.assertTrue(study["dt_sensitivity_below_1pct"], study)

    def test_vacuum_ballistic_segment(self):
        c = Config()
        rows, summary = simulate(c)
        trailing = [r for r in rows if c.valve_open_s+0.01 < r["time_s"] < 1.2]
        self.assertGreater(len(trailing), 3)
        for a, b in zip(trailing[:-1], trailing[1:]):
            self.assertAlmostEqual(b["vertical_velocity_mps"] - a["vertical_velocity_mps"],
                                   -c.gravity_mps2 * (b["time_s"]-a["time_s"]),
                                   delta=1e-7)

    def test_cli_creates_independently_readable_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [sys.executable, "-m", "simwhy", "run",
                 "examples/pressurized_jump.json", "--out", tmp],
                capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            for name in ("trajectory.csv", "trajectory.svg", "summary.json"):
                self.assertTrue((Path(tmp)/name).is_file())
            report = json.loads((Path(tmp)/"summary.json").read_text())
            self.assertGreater(report["peak_altitude_m"], 0)
            self.assertIn("NOT_HARDWARE_VALIDATED", report["status"])


if __name__ == "__main__":
    unittest.main()
