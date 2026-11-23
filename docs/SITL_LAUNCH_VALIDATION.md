# AVIO — three-PX4 SITL launcher validation

**Scope:** Linux multi-vehicle launch template, not flight automation. The script never issues arming, takeoff, Offboard mode or setpoints.

The official PX4 Gazebo multi-vehicle instructions use a unique `-i` instance, `PX4_SIM_MODEL=gz_x500`, and `PX4_GZ_STANDALONE=1` for vehicles 2 and 3 after the first starts Gazebo. See https://docs.px4.io/v1.18/en/sim_gazebo_gz/multi_vehicle_simulation and pin a compatible PX4 release before execution.

## Review the planned processes without dependencies

```sh
bash -n scripts/launch_three_px4.sh
PX4_DIR="$HOME/PX4-Autopilot" bash scripts/launch_three_px4.sh --dry-run
python3 -m unittest discover -s tests -v
```

The plan reports three distinct instances `-i 1/2/3`, model poses `(0,0)`, `(0,5)`, `(0,10)`, and separate logs. Dry-run intentionally does not check whether PX4 or Gazebo is installed and **does not launch anything**.

## Actual SITL capture (must be run on a prepared Linux host)

```sh
export PX4_DIR="$HOME/PX4-Autopilot"
export AVIO_SITL_LOG_DIR="$PWD/artifacts/sitl/session"
bash scripts/sitl_preflight.sh
bash scripts/launch_three_px4.sh
```

In other shells start the matching `MicroXRCEAgent` and observe `/uav_1`, `/uav_2`, `/uav_3` via the read-only ROS 2 observer as documented in `docs/SITL_CAPTURE_READINESS.md`.

A child process being alive does **not** demonstrate Gazebo model creation, DDS link, valid pose, or reliable flight. Logs and ROS 2 data require separate validation. Script shutdown sends SIGTERM to all tracked process IDs; inspect and terminate any descendant Gazebo processes in accordance with PX4's own tooling if necessary.

## Acceptance gates
1. GitHub CI passes Python tests plus Bash syntax and dry-run regression tests.
2. Three PX4 instances actually run on a pinned compatible Linux environment, with a visible Gazebo scene.
3. Three valid ROS 2 streams and a real ROS bag are collected, with exact toolchain versions and audit report.
4. Failure scenarios including missing/delayed telemetry, process termination, and operator abort are observed and documented.
5. Only then consider separate SITL-only offboard control and its required heartbeat/failsafe validation.

This release does not satisfy gates 2–5.
