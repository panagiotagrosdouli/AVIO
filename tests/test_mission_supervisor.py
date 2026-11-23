import unittest
from avio_mvp.mission_supervisor import Mission, Observation, Phase, VEHICLES

def feed(m, t, valid=True, vehicle=None):
    for v in ((vehicle,) if vehicle else VEHICLES):
        m.observe(Observation(v, t, valid, valid, (0., 0., 6.)))

def ready(m):
    m.begin_preflight(0.)
    feed(m, 0.)
    assert m.check_preflight(0.)
    assert m.start(0.)

class SupervisorTests(unittest.TestCase):
    def test_requires_all_three_healthy_agents(self):
        m = Mission()
        m.begin_preflight(0.)
        feed(m, 0., vehicle="uav_1")
        self.assertFalse(m.check_preflight(0.))
        self.assertEqual(m.phase, Phase.PREFLIGHT)

    def test_complete_requires_all_waypoints(self):
        m = Mission()
        ready(m)
        for v in VEHICLES:
            for i in range(3):
                self.assertTrue(m.waypoint_reached(v, 0.5))
        self.assertEqual(m.phase, Phase.COMPLETED)
        self.assertEqual(m.report()["completed_waypoints"], {v: 3 for v in VEHICLES})

    def test_stale_telemetry_hold_requires_explicit_resume(self):
        m = Mission(stale_after_s=2.)
        ready(m)
        self.assertEqual(m.tick(3.), Phase.HOLD)
        feed(m, 3.1)
        self.assertEqual(m.tick(3.1), Phase.HOLD)
        self.assertTrue(m.resume(3.1))
        self.assertEqual(m.phase, Phase.RUNNING)

    def test_bad_position_blocks_resume(self):
        m = Mission()
        ready(m)
        self.assertEqual(m.tick(3.), Phase.HOLD)
        feed(m, 3.1, valid=False)
        self.assertFalse(m.resume(3.1))
        self.assertEqual(m.phase, Phase.HOLD)

    def test_outside_local_bounds_causes_hold(self):
        m = Mission()
        ready(m)
        m.observe(Observation("uav_1", 1., True, True, (100., 0., 6.)))
        self.assertEqual(m.tick(1.), Phase.HOLD)

    def test_abort_terminal(self):
        m = Mission()
        ready(m)
        self.assertTrue(m.abort(0.5, "simulated_operator_abort"))
        self.assertEqual(m.phase, Phase.ABORTED)
        with self.assertRaises(ValueError):
            m.resume(1.)

    def test_non_monotonic_rejected(self):
        m = Mission()
        feed(m, 1.)
        with self.assertRaises(ValueError):
            feed(m, 1., vehicle="uav_1")

    def test_timeout_aborts(self):
        m = Mission(max_duration_s=5., stale_after_s=1.)
        ready(m)
        self.assertEqual(m.tick(6.), Phase.ABORTED)

    def test_invalid_waypoint_credit_not_allowed(self):
        m = Mission()
        with self.assertRaises(ValueError):
            m.waypoint_reached("uav_1", 0.)

    def test_no_command_capabilities(self):
        m = Mission()
        self.assertIn("NO_PX4_COMMANDS", m.report()["mode"])
        self.assertFalse(hasattr(m, "arm"))
        self.assertFalse(hasattr(m, "publish_setpoint"))

if __name__ == "__main__":
    unittest.main()
