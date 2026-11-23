import unittest
from avio_mvp.mission_demo import demo

class DemoTests(unittest.TestCase):
    def test_mission_demo_completes(self):
        result = demo()
        self.assertEqual(result["phase"], "completed")
        self.assertEqual(sum(result["completed_waypoints"].values()), 9)
        self.assertEqual(result["mode"], "ADVISORY_ONLY_NO_PX4_COMMANDS")

if __name__ == "__main__":
    unittest.main()
