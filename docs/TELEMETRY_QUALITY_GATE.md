# AVIO — three-UAV telemetry quality gate

**Purpose:** reject poor-quality PX4 observer recordings before treating them as useful diagnostic input. This is not a substitute for a real Gazebo/PX4/ROS 2 run, and does not authenticate the original data source.

## Checks
- Three distinct vehicle IDs `uav_1`, `uav_2`, `uav_3` must each meet the minimum sample count.
- Every accepted sample must carry AVIO's observer source, local ENU frame tag, valid UTC reception time, monotonically increasing per-UAV PX4 timestamps and finite XYZ values.
- Per-UAV reception gaps and reception-time coverage must meet configurable limits.
- A non-decreasing *overall reception order* is required for use with the offline supervisor adapter.

## Run
```bash
python3 -m unittest discover -s tests -v
python3 -m integrations.ros2.telemetry_quality \
  artifacts/sitl/session/telemetry.jsonl \
  --minimum-samples 10 \
  --maximum-gap-s 2.5 \
  --minimum-span-s 1.0 \
  --out artifacts/sitl/telemetry-quality.json
```

**Pass** means only that a source-labelled JSONL sequence satisfies these offline metrics. It does not prove three running PX4 instances, working Gazebo physics, vehicle safety, synchronized time, aligned local coordinate frames or actual motion. The origin of the JSONL messages must be independently verified using PX4 process logs, ROS bags and the official PX4 multi-vehicle guide.

A gap measured in UTC reception timestamps may reflect host scheduling, buffering or DDS transport effects rather than a PX4 failure. It is still useful as an observability diagnostic. Choosing limits requires actual measured PX4/SITL rates; the defaults are provisional and are not safety thresholds.
