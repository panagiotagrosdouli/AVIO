"""Launcher plan regression tests require Bash, not PX4/Gazebo."""
import os
from pathlib import Path
import subprocess
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "launch_three_px4.sh"

class LauncherPlanTests(unittest.TestCase):
    def test_shell_syntax(self):
        result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_dry_run_has_three_distinct_instances_and_model_poses(self):
        env = {**os.environ, "PX4_DIR": "/missing/px4",
               "AVIO_SITL_LOG_DIR": "relative_capture"}
        result = subprocess.run(["bash", str(SCRIPT), "--dry-run"],
                                env=env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("NOT EXECUTED", result.stdout)
        for i, pose in ((1, "0,0"), (2, "0,5"), (3, "0,10")):
            line = next(x for x in result.stdout.splitlines() if x.startswith(f"uav_{i}:"))
            self.assertIn(f"-i {i}", line)
            self.assertIn(pose.replace(',', r'\,'), line)
            self.assertIn(f"uav_{i}.log", line)
        self.assertEqual(result.stdout.count("PX4_GZ_STANDALONE=1"), 2)

    def test_invalid_startup_delay_rejected(self):
        env = {**os.environ, "AVIO_STARTUP_DELAY_SECONDS": "-3"}
        result = subprocess.run(["bash", str(SCRIPT), "--dry-run"],
                                env=env, capture_output=True, text=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)

    def test_extra_arguments_rejected(self):
        result = subprocess.run(["bash", str(SCRIPT), "--dry-run", "arm"],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)

if __name__ == "__main__":
    unittest.main()
