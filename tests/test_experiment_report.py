import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from integrations.ros2.evidence_gate import sha256_file
from integrations.ros2.experiment_report import build_experiment_report

NAMES=("uav_1","uav_2","uav_3")

def session(folder, *, moving=False):
    root=Path(folder)
    t0=datetime(2026,11,23,12,tzinfo=timezone.utc)
    data=[]
    for step in range(6):
        for vehicle in NAMES:
            data.append({
                "vehicle":vehicle,"source":"px4_ros2_observed",
                "frame":"vehicle_local_ENU_converted_from_NED_NOT_fleet_aligned",
                "received_at":(t0+timedelta(seconds=step*0.5)).isoformat(),
                "px4_timestamp_us":step*500000+1000000,
                "position_m":{"x":float(step)*0.4 if moving else 0.0,
                              "y":0.0,"z":6.0}
            })
    files={"telemetry_jsonl":("telemetry.jsonl",
                              "".join(json.dumps(e)+"\n" for e in data)),
           "px4_log_1":("uav_1.log","synthetic fixture\n"),
           "px4_log_2":("uav_2.log","synthetic fixture\n"),
           "px4_log_3":("uav_3.log","synthetic fixture\n"),
           "rosbag_metadata":("metadata.yaml","fixture metadata\n")}
    artifacts={}
    for key,(filename,content) in files.items():
        p=root/filename
        p.write_text(content)
        artifacts[key]={"path":filename,"sha256":sha256_file(p)}
    manifest=root/"manifest.json"
    manifest.write_text(json.dumps({"versions":{
        "px4_commit":"fixture","px4_msgs_commit":"fixture",
        "ros_distro":"fixture","gazebo_version":"fixture","agent_version":"fixture"
    },"artifacts":artifacts}))
    return manifest

class ExperimentReportTests(unittest.TestCase):
    def test_stationary_trial_data_gate_no_sitl_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            report=build_experiment_report(session(folder),minimum_samples=6)
            self.assertTrue(report["data_gate_passed"],report["issues"])
            self.assertFalse(report["real_sitl_verified"])
            self.assertIsNone(report["motion_evidence"])
            self.assertEqual(report["supervisor"]["post_simulated_outage_state"],"hold")
            self.assertTrue(all(x=="NOT_VERIFIED"
                                for x in report["independent_acceptance"].values()))

    def test_stationary_samples_fail_movement_trial(self):
        with tempfile.TemporaryDirectory() as folder:
            report=build_experiment_report(session(folder),kind="movement",
                                           minimum_samples=6)
            self.assertFalse(report["data_gate_passed"])
            self.assertFalse(report["motion_evidence"]["passed"])

    def test_movement_trial_passes_only_data_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            report=build_experiment_report(session(folder,moving=True),
                                           kind="movement",minimum_samples=6)
            self.assertTrue(report["data_gate_passed"],report["issues"])
            self.assertFalse(report["real_sitl_verified"])
            self.assertTrue(report["motion_evidence"]["passed"])

    def test_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest=session(folder,moving=True)
            (Path(folder)/"telemetry.jsonl").write_text("{}\n")
            report=build_experiment_report(manifest,kind="movement",minimum_samples=6)
            self.assertFalse(report["data_gate_passed"])
            self.assertTrue(any("digest" in x.lower() or "sha256" in x.lower()
                                for x in report["issues"]))

    def test_missing_manifest_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            report=build_experiment_report(Path(folder)/"missing.json",minimum_samples=6)
            self.assertFalse(report["data_gate_passed"])

    def test_bad_kind_rejected(self):
        with self.assertRaises(ValueError):
            build_experiment_report("irrelevant",kind="real_world")

if __name__=="__main__":
    unittest.main()
