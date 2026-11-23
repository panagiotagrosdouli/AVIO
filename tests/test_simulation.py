import json
import tempfile
import unittest
from pathlib import Path
from avio_mvp.__main__ import simulate, write_artifacts

class MissionTests(unittest.TestCase):
    def test_three_uavs_nine_unique_targets(self):
        r = simulate()
        self.assertEqual(len(r["vehicles"]), 3)
        self.assertEqual(len(r["observations"]), 9)
        self.assertEqual(len({o["target_id"] for o in r["observations"]}), 9)
        self.assertEqual(r["summary"]["coverage_pct"], 100)
        self.assertEqual(r["summary"]["separation_violations"], 0)
    def test_synthetic_evidence(self):
        r = simulate()
        self.assertIn("NOT_PX4_SITL",r["mode"])
        self.assertTrue(all(o["source"]=="deterministic_scenario_fixture" for o in r["observations"]))
        self.assertEqual(r["summary"]["review_required"], 1)
    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            simulate(speed=0)
    def test_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_artifacts(simulate(),tmp)
            self.assertEqual(len(json.loads((Path(tmp)/"latest.json").read_text())["observations"]),9)
            self.assertIn("SYNTHETIC ONLY",(Path(tmp)/"inspection-report.md").read_text())
if __name__=="__main__":
    unittest.main()
