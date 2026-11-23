# AVIO — Live telemetry monitoring (local-only, read-only)

**Status:** software bridge implemented. Unit tests use synthetic records; there is no demonstrated end-to-end PX4 SITL session or real flight.

## Architecture
PX4 SITL → uXRCE-DDS → ROS 2 VehicleLocalPosition → AVIO observer JSONL → local HTTP bridge → Mission Control browser polling.

The bridge is not a ROS 2 publisher, flight controller or inspection system. The HTTP endpoint exposes only sanitized local positional events, bound to 127.0.0.1 on port 8765. Browser polls once a second and labels samples stale beyond the configured three-second threshold. Incoming source labels are not authenticated.

## Run
After installing and validating PX4 SITL, Gazebo, ROS 2 and version-matched px4_msgs (see `docs/PHASE1B_EXECUTION.md`), source your ROS 2 environment and use two separate terminals from the AVIO repository root:

Terminal 1:
```bash
mkdir -p artifacts/sitl
python3 -m integrations.ros2.observer --output artifacts/sitl/telemetry.jsonl
```

Terminal 2:
```bash
python3 -m integrations.ros2.live_bridge --input artifacts/sitl/telemetry.jsonl --port 8765
```

Open `http://127.0.0.1:8765/` in a local browser.

For software validation without PX4:
```bash
python3 -m unittest discover -s tests -v
```

## Safety and limitations
- The page shows three **independent, auto-scaled local frames**. The local origins and clocks are not fleet-aligned. Never calculate cross-UAV distance or collision risk from these positions.
- There is no command endpoint and no direct flight-control logic.
- Missing file/vehicle is indicated as missing; timestamps older than three seconds are marked stale; partial and malformed JSONL lines are ignored.
- This is a local development server, not for internet exposure. Do not use for real aircraft operations.
- Validate sensor rates, communication loss, coordinate transform, operator failsafes and a recorded, reproducible Gazebo run before treating this as an integrated SITL demonstration.

## Primary upstream documentation
- https://docs.px4.io/main/en/ros2/multi_vehicle
- https://docs.px4.io/main/en/ros2/user_guide
- https://docs.python.org/3/library/http.server.html
