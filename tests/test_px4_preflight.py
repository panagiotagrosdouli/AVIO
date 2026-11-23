import unittest
from types import SimpleNamespace
from integrations.ros2.observer import topic_for, position_event
from integrations.ros2.check_topics import audit_topics

class PX4TelemetryContractTests(unittest.TestCase):
    def test_default_namespaces(self):
        self.assertEqual(topic_for(1),"/uav_1/fmu/out/vehicle_local_position")
        self.assertEqual(topic_for(3),"/uav_3/fmu/out/vehicle_local_position")
    def test_graph_preflight(self):
        names=[topic_for(i) for i in (1,2,3)]
        self.assertTrue(audit_topics(names)["ready"])
        self.assertEqual(audit_topics(names[:2])["missing"],[names[2]])
    def test_event_provenance_and_coordinates(self):
        m=SimpleNamespace(x=2.0,y=3.0,z=-4.0,xy_valid=True,z_valid=True,timestamp=1234)
        event=position_event(2,m)
        self.assertEqual(event["vehicle"],"uav_2")
        self.assertEqual(event["position_m"],{"x":3.0,"y":2.0,"z":4.0})
        self.assertIn("NOT_fleet_aligned",event["frame"])
    def test_invalid_position_ignored(self):
        m=SimpleNamespace(x=2,y=3,z=-4,xy_valid=False,z_valid=True,timestamp=5)
        self.assertIsNone(position_event(1,m))
if __name__=="__main__":
    unittest.main()
