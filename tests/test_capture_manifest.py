import json
import tempfile
import unittest
from pathlib import Path
from integrations.ros2.capture_manifest import ARTIFACTS, build_manifest, sha256_file

VERSIONS = {"px4_commit": "a"*40, "px4_msgs_commit": "b"*40,
            "ros_distro": "jazzy", "gazebo_version": "verified locally",
            "agent_version": "verified locally"}

class CaptureManifestTests(unittest.TestCase):
    def test_missing_evidence_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = build_manifest(tmp, VERSIONS)
            self.assertFalse(result["capture_readiness"]["complete"])
            self.assertEqual(len(result["capture_readiness"]["missing"]), 5)

    def test_complete_files_and_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            for filename in ARTIFACTS.values():
                (Path(tmp)/filename).write_text("fixture, not actual PX4\n")
            result = build_manifest(tmp, VERSIONS)
            self.assertTrue(result["capture_readiness"]["complete"])
            self.assertEqual(len(result["artifacts"]), 5)
            for entry in result["artifacts"].values():
                self.assertEqual(len(entry["sha256"]), 64)

    def test_version_must_not_be_invented(self):
        with tempfile.TemporaryDirectory() as tmp:
            for filename in ARTIFACTS.values():
                (Path(tmp)/filename).write_text("fixture\n")
            result = build_manifest(tmp, {**VERSIONS, "px4_commit": None})
            self.assertIn("versions.px4_commit", result["capture_readiness"]["missing"])

    def test_hash_detects_file_edit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"test.log"
            path.write_text("A")
            first = sha256_file(path)
            path.write_text("B")
            self.assertNotEqual(first, sha256_file(path))

if __name__ == "__main__":
    unittest.main()
