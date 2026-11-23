# AVIO three-UAV PX4/Gazebo evidence gate

**Status: offline audit tool implemented; actual three-PX4 end-to-end validation NOT performed.** This gate can reject incomplete or altered captures; it cannot independently prove that recorded input came from PX4/Gazebo.

## Prerequisites and official baseline

Pin matching versions of PX4, px4_msgs, ROS 2, Gazebo, Micro XRCE-DDS Agent and Fast DDS. The agent/client version pairing matters: consult https://docs.px4.io/main/en/middleware/uxrce_dds for the selected PX4 release. Multi-vehicle namespace defaults for PX4 instances 1/2/3 are `uav_1`, `uav_2`, `uav_3` if not overridden: https://docs.px4.io/main/en/ros2/multi_vehicle.

Do not interpret a ROS 2 graph listing as evidence of three active vehicles. Record running PX4 processes, Gazebo models, uXRCE agent output, ROS bag and the read-only observer JSONL from the same session.

## 1. Prepare a real captured session

Run the setup documented in `docs/PHASE1B_EXECUTION.md`. Capture **at least 10** valid local-position messages from each distinct instance, including UTC `received_at` fields. Ensure PX4 timestamps increase within each stream and that the observer lines are in nondecreasing UTC reception order. Collect:

- `uav_1.log`, `uav_2.log`, `uav_3.log` from separate PX4 SITL instances.
- `telemetry.jsonl` written by `python3 -m integrations.ros2.observer --output <path>`.
- `metadata.yaml` from a **real ROS bag** recorded alongside the session.
- Release/commit manifest (not the string `main`) for PX4 and px4_msgs, plus ROS distro, Gazebo version and DDS agent version.

The log files alone can be spoofed or replayed. A successful result is **file/data integrity only**. A human reviewer must independently verify running instances, Gazebo model identity, real rosbag messages, time alignment and induced link-loss/recovery behavior.

## 2. Create a manifest next to the captured files

Save `artifacts/sitl/session/manifest.json` as follows (replace all placeholders):

```json
{
  "versions": {
    "px4_commit": "actual git commit hash",
    "px4_msgs_commit": "matching message repo commit",
    "ros_distro": "jazzy",
    "gazebo_version": "version as installed",
    "agent_version": "agent version as installed"
  },
  "artifacts": {
    "telemetry_jsonl": {"path": "telemetry.jsonl", "sha256": "64-character SHA-256"},
    "px4_log_1": {"path": "uav_1.log", "sha256": "64-character SHA-256"},
    "px4_log_2": {"path": "uav_2.log", "sha256": "64-character SHA-256"},
    "px4_log_3": {"path": "uav_3.log", "sha256": "64-character SHA-256"},
    "rosbag_metadata": {"path": "metadata.yaml", "sha256": "64-character SHA-256"}
  }
}
```

From `artifacts/sitl/session`, get the corresponding digests using:

```bash
sha256sum telemetry.jsonl uav_1.log uav_2.log uav_3.log metadata.yaml
```

Only relative paths within the manifest directory are accepted. The file hash establishes integrity since the manifest was created, **not authenticity**.

## 3. Audit session and induce an *offline* outage

```bash
python3 -m unittest discover -s tests -v
python3 -m integrations.ros2.evidence_gate \
  artifacts/sitl/session/manifest.json \
  --minimum-samples 10 \
  --report artifacts/sitl/evidence-audit.json
```

A valid dataset yields `data_gate_passed: true` and individual checks. The tool evaluates an advisory-only supervisor with a simulated four-second silence after the last event: it must end in `HOLD`, without auto-resume or synthetic waypoint credits. This is **not an actual induced DDS/flight-control failure**. Exit code 1 means the data gate failed.

## 4. Remaining independent acceptance gates

1. Reproducible launch logs confirm three unique PX4 SITL processes and corresponding Gazebo models, not just filenames.
2. The ROS bag really contains samples from all three namespaces, with matching PX4 message types.
3. Source-side timestamps and coordinate frames are audited; each local ENU origin is not treated as a common fleet frame.
4. A separately observed and documented uXRCE-DDS interruption produces expected read-only monitoring/supervisor behavior.
5. Independent review of PX4 failsafe configuration; no live Offboard commands have been issued by AVIO.

**Offboard control remains outside this work.** PX4 demands a >2 Hz proof-of-life stream before and during Offboard mode and specified offboard-loss actions; see https://docs.px4.io/main/en/flight_modes/offboard. No claim of autonomy, collision avoidance, defect detection or hardware validation follows from this tool.
