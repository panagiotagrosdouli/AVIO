import unittest
from datetime import datetime, timedelta, timezone
from integrations.ros2.motion_evidence import audit_motion

ORIGIN=datetime(2026,11,23,tzinfo=timezone.utc)
VEHICLES=("uav_1","uav_2","uav_3")

def entry(name,t,x):
    return {"source":"px4_ros2_observed","vehicle":name,
            "frame":"vehicle_local_ENU_converted_from_NED_NOT_fleet_aligned",
            "received_at":(ORIGIN+timedelta(seconds=t)).isoformat(),
            "px4_timestamp_us":int((t+1)*1e6),
            "position_m":{"x":float(x),"y":0.0,"z":6.0}}

def moving():
    return [entry(name,t,t*0.8) for t in (0,0.5,1,1.5,2)
            for name in VEHICLES]

class MotionEvidenceTests(unittest.TestCase):
    def test_three_independent_local_tracks_pass(self):
        result=audit_motion(moving(),minimum_samples=5)
        self.assertTrue(result["passed"],result["issues"])
        self.assertFalse(result["gazebo_execution_verified"])
        self.assertFalse(result["physical_flight_verified"])
        for name in VEHICLES:
            self.assertGreater(result["vehicles"][name]["net_displacement_m"],1)

    def test_stationary_vehicle_fails(self):
        events=moving()
        for e in events:
            if e["vehicle"]=="uav_3":
                e["position_m"]["x"]=0
        result=audit_motion(events,minimum_samples=5)
        self.assertFalse(result["passed"])
        self.assertFalse(result["vehicles"]["uav_3"]["movement_gate_passed"])

    def test_jitter_not_counted_as_motion(self):
        events=moving()
        for e in events:
            e["position_m"]["x"]=(e["px4_timestamp_us"]%3)*0.001
        report=audit_motion(events,minimum_samples=5,
                            minimum_displacement_m=0.1,minimum_path_m=0.1)
        self.assertFalse(report["passed"])

    def test_one_missing_vehicle_fails(self):
        events=[e for e in moving() if e["vehicle"]!="uav_2"]
        self.assertFalse(audit_motion(events,minimum_samples=5)["passed"])

    def test_reception_gap_fails(self):
        events=moving()
        events.extend(entry(name,10,8.0) for name in VEHICLES)
        report=audit_motion(events,minimum_samples=5,maximum_gap_s=2.5)
        self.assertFalse(report["passed"])
        self.assertTrue(any("gap" in issue for issue in report["issues"]))

    def test_out_of_order_fails(self):
        events=moving()
        events[2],events[3]=events[3],events[2]
        # Same timestamp swap alone is valid, so reverse different time slots.
        events[0],events[-1]=events[-1],events[0]
        self.assertFalse(audit_motion(events,minimum_samples=5)["passed"])

    def test_invalid_coordinate_fails(self):
        events=moving()
        events[3]["position_m"]["x"]=float("nan")
        self.assertFalse(audit_motion(events,minimum_samples=5)["passed"])

    def test_invalid_threshold_fails(self):
        with self.assertRaises(ValueError):
            audit_motion(moving(),jitter_deadband_m=float("nan"))

if __name__=="__main__":
    unittest.main()
