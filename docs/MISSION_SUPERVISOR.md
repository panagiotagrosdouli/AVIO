# AVIO three-UAV mission supervisor — software-only prototype

## Status
Implemented as a deterministic Python state machine with no ROS 2 or PX4 publishers.
There is **no actual mission execution or offboard flight**. A waypoint is counted only
when the caller explicitly supplies a synthetic `waypoint_reached` event. No tracking
controller or geometric arrival detector is present.

## Run
```bash
python3 -m unittest discover -s tests -v
python3 -m avio_mvp.mission_demo
cat artifacts/mission-supervisor-demo.json
```
Run from repository root, Python 3.10+.

## Lifecycle
`IDLE` → `PREFLIGHT` → `READY` → `RUNNING` → `COMPLETED`.
Missing/stale telemetry, invalid position or local-bound breach during running
causes `HOLD`. Only explicit `resume()` with healthy samples returns to
`RUNNING`. A mission deadline causes terminal `ABORTED`. `abort()`
is an advisory state change **not a PX4 command**.

## Gates
- All three vehicle IDs must have valid local x/y/z and fresh monotonic timestamps.
- No automatic recovery after a hold.
- No waypoint progress accepted outside RUNNING.
- Completion requires all configured per-vehicle waypoint credits.
- Failures and transitions are appended to a structured event log.

## Safety/semantic boundaries
Local XYZ geofence checks apply separately to each reported coordinate frame.
Without verified common frame alignment, these are **not shared global
geofences**. No inter-vehicle separation can be inferred, and the example
does not assert that any UAV actually reached a waypoint.

This component is deliberately not wired to offboard control. PX4 requires a
continuous proof-of-life stream at greater than 2 Hz, active before entering
Offboard mode, and has offboard-loss failsafe settings. Real flight control
requires explicit verification of mode transitions, vehicle identity, time
sources, failsafe configuration, simulated hazards and operator oversight.

Upstream:
- https://docs.px4.io/main/en/flight_modes/offboard
- https://docs.px4.io/main/en/ros2/offboard_control

## Next integration gate
1. Run with three *real* PX4 SITL telemetry streams and preserved vehicle origins.
2. Validate local geofence applicability per vehicle.
3. Add explicit independent waypoint-detection logic and mission event provenance.
4. Only after safety review, implement isolated SITL offboard commands and
   verify continuity, heartbeat-loss behavior, failsafe and emergency stop.
5. Do not connect to physical vehicles from this prototype.
