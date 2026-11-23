import unittest
from datetime import datetime, timedelta, timezone
from integrations.ros2.telemetry_quality import audit_quality

START = datetime(2026, 11, 23, tzinfo=timezone.utc)
VEHICLES = ("uav_1", "uav_2", "uav_3")

def entry(vehicle, second, timestamp=None):
    return {"vehicle": vehicle, "source": "px4_ros2_observed",
            "frame": "vehicle_local_ENU_converted_from_NED_NOT_fleet_aligned",
            "received_at": (START + timedelta(seconds=second)).isoformat(),
            "px4_timestamp_us": int(second*1e6) if timestamp is None else timestamp,
            "position_m": {"x": 1.0, "y": 2.0, "z": 3.0}}

def clean():
    return [entry(vehicle, second) for second in (0, 0.5, 1.0, 1.5)
            for vehicle in VEHICLES]

class TelemetryQualityTests(unittest.TestCase):
    def test_healthy_three_stream_fixture(self):
        report = audit_quality(clean(), minimum_samples=4, maximum_gap_s=1,
                               minimum_span_s=1)
        self.assertTrue(report["passed"], report["issues"])
        self.assertFalse(report["gazebo_execution_verified"])

    def test_missing_vehicle_rejected(self):
        events = [e for e in clean() if e["vehicle"] != "uav_3"]
        self.assertFalse(audit_quality(events, 4, 1, 1)["passed"])

    def test_gap_detected_even_after_recovery(self):
        events = clean()
        events += [entry(v, 5) for v in VEHICLES]
        report = audit_quality(events, 4, 1, 1)
        self.assertFalse(report["passed"])
        self.assertTrue(any("gap" in x for x in report["issues"]))

    def test_timestamp_replay_rejected(self):
        events = clean()
        events += [entry(v, 2, 1) for v in VEHICLES]
        self.assertFalse(audit_quality(events, 4, 1, 1)["passed"])

    def test_bad_position_rejected(self):
        events = clean()
        events[2]["position_m"]["z"] = float("nan")
        self.assertFalse(audit_quality(events, 4, 1, 1)["passed"])

    def test_forged_source_flag_rejected(self):
        events = clean()
        events[0]["source"] = "fixture"
        self.assertFalse(audit_quality(events, 4, 1, 1)["passed"])

    def test_out_of_order_receipt_rejected(self):
        events = clean()
        events[3], events[4] = events[4], events[3]
        self.assertFalse(audit_quality(events, 4, 1, 1)["passed"])

    def test_short_span_rejected(self):
        self.assertFalse(audit_quality(clean(), 4, 1, 2)["passed"])

    def test_invalid_threshold_rejected(self):
        with self.assertRaises(ValueError):
            audit_quality(clean(), maximum_gap_s=float("nan"))

if __name__ == "__main__":
    unittest.main()
