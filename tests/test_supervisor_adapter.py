import unittest
from datetime import datetime, timedelta, timezone
from integrations.ros2.supervisor_adapter import evaluate_recording

START = datetime(2026, 11, 23, 10, tzinfo=timezone.utc)
NAMES = ("uav_1", "uav_2", "uav_3")

def event(name, second, px4stamp=None):
    return {
        "vehicle": name, "source": "px4_ros2_observed",
        "frame": "vehicle_local_ENU_converted_from_NED_NOT_fleet_aligned",
        "position_m": {"x": 0.0, "y": 0.0, "z": 6.0},
        "received_at": (START + timedelta(seconds=second)).isoformat(),
        "px4_timestamp_us": int(second*1000000) if px4stamp is None else px4stamp
    }

def fleet(seconds):
    return [event(name, t) for t in seconds for name in NAMES]

class RecordedSupervisorTests(unittest.TestCase):
    def test_three_streams_preflight_ready_without_auto_start(self):
        r = evaluate_recording(fleet([0, 0.5]))
        self.assertEqual(r["phase"], "ready")
        self.assertFalse(r["autonomous_flight"])
        self.assertEqual(sum(r["accepted_samples"].values()), 6)
        self.assertEqual(sum(r["completed_waypoints"].values()), 0)

    def test_explicit_advisory_start(self):
        r = evaluate_recording(fleet([0, 0.5, 1.0]), start_advisory=True)
        self.assertEqual(r["phase"], "running")
        self.assertEqual(sum(r["completed_waypoints"].values()), 0)

    def test_silence_causes_hold(self):
        r = evaluate_recording(fleet([0, 0.5]), start_advisory=True, end_gap_s=4)
        self.assertEqual(r["phase"], "hold")
        self.assertTrue(any("automatic_hold:" in e["event"] for e in r["events"]))

    def test_recovery_does_not_resume(self):
        r = evaluate_recording(fleet([0, 0.5, 4, 4.1]), start_advisory=True)
        self.assertEqual(r["phase"], "hold")
        self.assertFalse(any("resume" in e["event"] for e in r["events"]))

    def test_missing_vehicle_stays_preflight(self):
        r = evaluate_recording([event("uav_1", 0), event("uav_2", 0)],
                               start_advisory=True)
        self.assertEqual(r["phase"], "preflight")

    def test_nonmonotonic_px4_stamp_fails_closed(self):
        r = evaluate_recording(fleet([0, 0.5]) + [event("uav_1", 0.6, 1)],
                               start_advisory=True)
        self.assertEqual(r["phase"], "hold")
        self.assertEqual(r["rejected_samples"], 1)

    def test_invalid_source_triggers_hold(self):
        events = fleet([0])
        bad = event("uav_1", 0.2)
        bad["source"] = "synthetic_fixture"
        r = evaluate_recording(events + [bad], start_advisory=True)
        self.assertEqual(r["phase"], "hold")

    def test_out_of_order_receipt_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_recording([event("uav_1", 1), event("uav_2", 0)])

    def test_unsupported_negative_gap(self):
        with self.assertRaises(ValueError):
            evaluate_recording([], end_gap_s=-1)

    def test_empty_evidence_not_started(self):
        r = evaluate_recording([], start_advisory=True)
        self.assertEqual(r["phase"], "preflight")

if __name__ == "__main__":
    unittest.main()
