import unittest
from integrations.ros2.verify_telemetry import verify_records

def event(vehicle,ts):
    return {"vehicle":vehicle,"px4_timestamp_us":ts,
            "source":"px4_ros2_observed",
            "frame":"vehicle_local_ENU_converted_from_NED_NOT_fleet_aligned",
            "position_m":{"x":1.0,"y":2.0,"z":3.0}}

class TelemetryEvidenceTests(unittest.TestCase):
    def test_three_distinct_streams(self):
        records=[event(v,t) for t in (1,2,3) for v in ("uav_1","uav_2","uav_3")]
        self.assertTrue(verify_records(records,minimum_samples=3)["passed"])
    def test_missing_vehicle_fails(self):
        records=[event("uav_1",1),event("uav_2",1)]
        self.assertFalse(verify_records(records,minimum_samples=1)["passed"])
    def test_nonmonotonic_timestamp_fails(self):
        records=[event(v,2) for v in ("uav_1","uav_2","uav_3")]
        records.append(event("uav_1",1))
        self.assertFalse(verify_records(records,minimum_samples=1)["passed"])
    def test_provenance_fails(self):
        records=[event(v,1) for v in ("uav_1","uav_2","uav_3")]
        records[0]["source"]="synthetic"
        self.assertFalse(verify_records(records,minimum_samples=1)["passed"])

if __name__=="__main__":
    unittest.main()
