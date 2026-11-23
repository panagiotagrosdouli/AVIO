import unittest
from avio_mvp.benchmark import benchmark

class BenchmarkTests(unittest.TestCase):
    def test_synthetic_mission_regression(self):
        result = benchmark()
        self.assertTrue(result["passing"])
        self.assertEqual(result["fleet_size"], 3)
        self.assertEqual(result["target_count"], 9)
        self.assertEqual(result["static_grid_shortest_path_steps"], 6)
        self.assertIn("NOT PX4",result["scope"])

if __name__=="__main__":
    unittest.main()
