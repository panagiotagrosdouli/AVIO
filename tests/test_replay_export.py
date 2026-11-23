import json
import tempfile
import unittest
from pathlib import Path
from integrations.ros2.export_replay import export_replay

def recorded(vehicle, timestamp, x):
    return {"schema_version": "1.0", "source": "px4_ros2_observed",
            "vehicle": vehicle, "px4_timestamp_us": timestamp,
            "frame": "vehicle_local_ENU_converted_from_NED_NOT_fleet_aligned",
            "position_m": {"x": x, "y": 2, "z": 3}}

class ReplayExportTests(unittest.TestCase):
    def make_events(self):
        return [recorded(v, t, float(t)) for t in (10, 20, 30)
                for v in ("uav_1", "uav_2", "uav_3")]

    def test_split_vehicle_local_frames(self):
        report = export_replay(self.make_events(), minimum_samples=3)
        self.assertEqual(report["counts"]["uav_3"], 3)
        self.assertEqual(report["vehicles"]["uav_1"][0]["timestamp_us"], 10)
        self.assertEqual(report["reference_frame"], "per_vehicle_local_ENU_not_fleet_aligned")
        self.assertIsNone(report["inter_vehicle_separation_m"])
        self.assertIsNone(report["coverage_pct"])
        self.assertFalse(report["has_inspection_observations"])

    def test_missing_vehicle_fails_closed(self):
        with self.assertRaises(ValueError):
            export_replay(self.make_events()[:2], minimum_samples=1)

    def test_monotonic_violation_fails_closed(self):
        events = self.make_events()
        events.append(recorded("uav_1", 15, 0))
        with self.assertRaises(ValueError):
            export_replay(events, minimum_samples=1)

    def test_non_finite_coordinates_rejected(self):
        events = self.make_events()
        events[0]["position_m"]["x"] = float("nan")
        with self.assertRaises(ValueError):
            export_replay(events, minimum_samples=1)

    def test_json_serializable(self):
        replay = export_replay(self.make_events(), minimum_samples=1)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "replay.json"
            p.write_text(json.dumps(replay, allow_nan=False))
            self.assertEqual(len(json.loads(p.read_text())["vehicles"]), 3)

if __name__ == "__main__":
    unittest.main()
