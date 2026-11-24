import unittest
from avio_mvp.collaborative_perception import experiment, fuse, observe


class CollaborativePerceptionTests(unittest.TestCase):
    def test_reproducibility(self):
        self.assertEqual(experiment(42), experiment(42))

    def test_shared_coverage(self):
        for seed in range(20):
            result = experiment(seed)
            self.assertGreater(result["shared_coverage"], max(result["agent_coverage"]))
            self.assertLessEqual(result["shared_coverage"], 1.0)
            self.assertEqual(result["shared_accuracy_on_observed_cells"], 1.0)

    def test_fusion_union(self):
        self.assertEqual(fuse([{(0, 0): 0}, {(1, 0): 1}]), {(0, 0): 0, (1, 0): 1})

    def test_conflict(self):
        with self.assertRaises(ValueError):
            fuse([{(0, 0): 0}, {(0, 0): 1}])

    def test_sensor_radius(self):
        self.assertEqual(observe({(0, 0): 1, (19, 19): 0}, (0, 0)), {(0, 0): 1})


if __name__ == "__main__":
    unittest.main()
