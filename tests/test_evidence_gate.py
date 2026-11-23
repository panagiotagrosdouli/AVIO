import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from integrations.ros2.evidence_gate import audit, sha256_file

def make_bundle(folder):
    root = Path(folder)
    start = datetime(2026, 11, 23, 11, tzinfo=timezone.utc)
    events = []
    for tick in (0, 0.5, 1):
        for index in (1, 2, 3):
            events.append({
                "vehicle": f"uav_{index}", "source": "px4_ros2_observed",
                "frame": "vehicle_local_ENU_converted_from_NED_NOT_fleet_aligned",
                "px4_timestamp_us": int((tick+1)*1000000),
                "received_at": (start + timedelta(seconds=tick)).isoformat(),
                "position_m": {"x": 0, "y": 0, "z": 6}
            })
    contents = {"telemetry_jsonl": ("telemetry.jsonl",
                                    "".join(json.dumps(e)+"\n" for e in events))}
    for idx in (1, 2, 3):
        contents[f"px4_log_{idx}"] = (f"uav_{idx}.log", f"synthetic log {idx}\n")
    contents["rosbag_metadata"] = ("metadata.yaml", "synthetic bag metadata\n")
    artifacts = {}
    for key, (filename, body) in contents.items():
        destination = root/filename
        destination.write_text(body)
        artifacts[key] = {"path": filename, "sha256": sha256_file(destination)}
    manifest = {
        "versions": {
            "px4_commit": "synthetic-only", "px4_msgs_commit": "synthetic-only",
            "ros_distro": "synthetic-only", "gazebo_version": "synthetic-only",
            "agent_version": "synthetic-only"
        },
        "artifacts": artifacts
    }
    path = root/"manifest.json"
    path.write_text(json.dumps(manifest))
    return path

class EvidenceGateTests(unittest.TestCase):
    def test_fixture_passes_only_offline_data_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            result = audit(make_bundle(directory), minimum_samples=3)
            self.assertTrue(result["data_gate_passed"], result["findings"])
            self.assertTrue(result["no_autonomous_flight_claim"])
            self.assertTrue(result["requires_independent_review"])

    def test_hash_tampering_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = make_bundle(directory)
            (Path(directory)/"uav_2.log").write_text("tampered")
            result = audit(manifest, minimum_samples=3)
            self.assertFalse(result["data_gate_passed"])
            self.assertTrue(any("mismatch" in x for x in result["findings"]))

    def test_missing_artifact_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = make_bundle(directory)
            (Path(directory)/"metadata.yaml").unlink()
            self.assertFalse(audit(manifest, minimum_samples=3)["data_gate_passed"])

    def test_missing_vehicle_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = make_bundle(directory)
            data = Path(directory)/"telemetry.jsonl"
            lines = [line for line in data.read_text().splitlines()
                     if json.loads(line)["vehicle"] != "uav_3"]
            data.write_text("\n".join(lines)+"\n")
            obj = json.loads(manifest.read_text())
            obj["artifacts"]["telemetry_jsonl"]["sha256"] = sha256_file(data)
            manifest.write_text(json.dumps(obj))
            self.assertFalse(audit(manifest, minimum_samples=3)["data_gate_passed"])

    def test_escape_path_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = make_bundle(directory)
            obj = json.loads(manifest.read_text())
            obj["artifacts"]["px4_log_1"]["path"] = "../elsewhere.log"
            manifest.write_text(json.dumps(obj))
            result = audit(manifest, minimum_samples=3)
            self.assertFalse(result["data_gate_passed"])
            self.assertTrue(any("escapes" in x for x in result["findings"]))

if __name__ == "__main__":
    unittest.main()
