# AVIO read-only telemetry-to-supervisor integration

## What is implemented
Offline conversion of a three-UAV ROS 2 observer JSONL recording into a mission-state transition report. This is **not** a flight controller, a ROS 2 publisher, a multi-drone localization system, or proof of actual PX4 SITL execution.

The adapter checks schema/provenance, per-vehicle PX4 timestamp monotonicity, UTC receipt-time ordering, and telemetry freshness. It uses the AVIO Mission Supervisor for `PREFLIGHT → READY` and, only when explicitly requested, an **advisory-only** `RUNNING` state. Missing/stale/rejected data lead to blocked preflight or `HOLD`. There is no automatic return from `HOLD`, no fabricated waypoint completion, and no takeoff/arming/position setpoints.

Important: the adapter uses **relative UTC receipt timestamps**, not synchronized PX4 vehicle clocks. The three local ENU frames remain *unaligned*. A local-bound check here is not a shared geofence, and no cross-UAV separation is computed. The source string is asserted by JSONL and is not independently authenticated.

## Run with a previously recorded session
```sh
python3 -m unittest discover -s tests -v

# Observe preflight readiness, without claiming mission start
python3 -m integrations.ros2.supervisor_adapter \
  artifacts/sitl/telemetry.jsonl \
  --out artifacts/sitl/supervisor-report.json

# Evaluate advisory RUNNING and a simulated four-second telemetry outage
python3 -m integrations.ros2.supervisor_adapter \
  artifacts/sitl/telemetry.jsonl \
  --start-advisory --end-gap 4 \
  --out artifacts/sitl/outage-report.json
```

In the reports, review `phase`, `events`, `accepted_samples`, `rejected_samples`, and `time_basis`. `--start-advisory` changes only an in-memory software state. It never arms or moves a UAV.

## Validation gate to advance
1. Pin PX4 / Gazebo / ROS 2 / px4_msgs versions and capture three independently validated SITL sources.
2. Collect a ROS bag plus observer JSONL and timestamps; demonstrate an induced DDS link interruption.
3. Confirm that the resulting mission report goes to `HOLD`, never automatically resumes, and does not claim waypoint completion.
4. Test loss of one vehicle, invalid local position, restarts, timestamp resets, latency spikes, and supervisor clock behavior.
5. Keep PX4 offboard flight commands in a separately reviewed SITL-only implementation. Do not use this component for physical flight.

## Known limitations
The JSONL event format does not carry direct source validity booleans; the ROS 2 observer filters those flags before output. A forged record could pass format checks, so evidence authentication is not provided. Source-to-receiver timing differences, replay gaps, stale buffers, and cross-vehicle frame/clock alignment need more extensive verification.
