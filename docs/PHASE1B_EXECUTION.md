# AVIO Phase 1B: reproducible three-PX4 telemetry gate

**Current state:** implementation scaffolding and contract tests. No recorded run from PX4/Gazebo/ROS 2 exists yet. The scripted launch is a template to validate on Linux; not an achieved hardware or autonomy milestone.

## Prerequisites
- Ubuntu/Linux with PX4-supported Gazebo and PX4-Autopilot built using `make px4_sitl`.
- ROS 2 with `rclpy`, and `px4_msgs` aligned to the PX4 source's DDS definitions.
- MicroXRCEAgent matching PX4 middleware requirements.
- Record full hashes / versions: PX4 (`git rev-parse HEAD`), `px4_msgs`, ROS distro, Gazebo version, agent version. Follow version-specific PX4 docs.

## Start up
Terminal A (one DDS agent for all three clients):
```bash
MicroXRCEAgent udp4 -p 8888
```

Terminal B (launches 3 PX4 processes using gz_x500 models):
```bash
PX4_DIR=$HOME/PX4-Autopilot bash scripts/launch_three_px4.sh
```

Terminal C (source ROS 2 and the workspace containing a matching `px4_msgs`):
```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
python3 -m integrations.ros2.check_topics
python3 -m integrations.ros2.observer --output artifacts/sitl/telemetry.jsonl
```

Observe nonempty, increasing JSONL samples for all three identities. After collecting a session, run:

```bash
python3 -m integrations.ros2.verify_telemetry artifacts/sitl/telemetry.jsonl --minimum-samples 10
```

A passing JSONL contract check is not proof of physical motion or a stable PX4 flight; inspect the Gazebo scene and source logs as well.

### Export the recorded Mission Control replay
```bash
python3 -m integrations.ros2.export_replay \
  artifacts/sitl/telemetry.jsonl \
  --out artifacts/sitl/replay.json --minimum-samples 10
python3 -m http.server 8000
```
Open `http://localhost:8000/mission-control/sitl.html`. It displays three **separate per-vehicle local ENU traces**, with independent sample index and no inter-vehicle distance calculations. The browser cannot authenticate the source; keep the source logs and version manifests. The generated replay is read-only and **not live**. The original `mission-control/` view continues to display only the synthetic inspection mission. Use Ctrl+C to stop observer/launcher. Store logs and versions alongside `artifacts/sitl`; do not commit large logs or sensitive telemetry.

## Technical limitations
- The observer is strictly read-only. No setpoints, arming, takeoff or mission control.
- It reports each PX4 *local* frame: `NED → ENU` swaps/sign-flips position only. Local origins may differ; do not compute fleet distance from these coordinates until origins and clocks are aligned and independently validated.
- The topic checker verifies graph topic presence/types, **not active telemetry delivery**; the observer log needs separate validation.
- Starting three processes is not proof of running three PX4 instances, stable operation or correctly aligned frames.
- The synthetic kinematic Mission Control remains separate; the offline PX4 replay view consumes converted JSON, not live ROS 2 streams. No common-origin or time alignment is asserted.

## Acceptance evidence needed
1. Output of `python3 -m unittest discover -s tests -v` and `python3 -m integrations.ros2.check_topics`.
2. PX4/Gazebo/agent version manifest and three SITL logs with individual identifiers.
3. Timestamped telemetry from all three topic streams, checked for monotonicity.
4. Saved ROS bag and screenshots/logs from a repeatable run.
5. Independent review of topic namespace, frame conventions, failsafes and simulation startup.

## Authoritative documentation
- https://docs.px4.io/main/en/ros2/multi_vehicle
- https://docs.px4.io/main/en/sim_gazebo_gz/multi_vehicle_simulation
- https://docs.px4.io/main/en/middleware/uxrce_dds
