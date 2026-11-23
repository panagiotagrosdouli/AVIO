import unittest
from integrations.ros2.observer import ned_to_enu

class PositionTransformTests(unittest.TestCase):
    def test_ned_position_to_enu(self):
        self.assertEqual(ned_to_enu(2, 3, -4), {"x":3.0,"y":2.0,"z":4.0})
    def test_origin(self):
        self.assertEqual(ned_to_enu(0,0,0),{"x":0.0,"y":0.0,"z":0.0})

if __name__=="__main__":
    unittest.main()
