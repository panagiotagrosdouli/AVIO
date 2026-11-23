import unittest
from avio_mvp.__main__ import simulate
from avio_mvp.validation import (plan_grid, path_geofence_valid,
                                 trajectory_conflicts, evaluate_inspection)

class PlanningTests(unittest.TestCase):
    def test_shortest_path_avoids_static_obstacle(self):
        path = plan_grid((0, 0), (2, 0), {(1, 0)}, 3, 3)
        self.assertEqual(path[0], (0, 0))
        self.assertEqual(path[-1], (2, 0))
        self.assertNotIn((1, 0), path)
        self.assertEqual(len(path), 5)
    def test_unreachable(self):
        self.assertIsNone(plan_grid((0, 0), (2, 0), {(1,0),(1,1),(1,2)},3,3))
    def test_invalid_grid(self):
        with self.assertRaises(ValueError):
            plan_grid((-1,0),(2,0),set(),3,3)
    def test_geofence(self):
        self.assertTrue(path_geofence_valid([(0,0),(1,2)],(0,0,2,2)))
        self.assertFalse(path_geofence_valid([(0,0),(3,2)],(0,0,2,2)))
    def test_separation_monitor(self):
        trajectories = {"a": [(0,0,0),(1,0,0)],"b":[(10,0,0),(1.5,0,0)]}
        alerts = trajectory_conflicts(trajectories,2.0)
        self.assertEqual(len(alerts),1)
        self.assertEqual(alerts[0]["sample"],1)
    def test_separation_shape_validation(self):
        with self.assertRaises(ValueError):
            trajectory_conflicts({"a":[(0,0,0)],"b":[]},2.0)
    def test_inspection_evidence(self):
        quality = evaluate_inspection(simulate())
        self.assertTrue(quality["passed"])
        self.assertEqual(quality["coverage_pct"],100)
    def test_duplicate_observation_rejected(self):
        mission = simulate()
        mission["observations"].append(dict(mission["observations"][0]))
        self.assertFalse(evaluate_inspection(mission)["passed"])
        self.assertEqual(len(evaluate_inspection(mission)["duplicate_observations"]),1)

if __name__ == "__main__":
    unittest.main()
