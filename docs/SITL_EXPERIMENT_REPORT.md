# AVIO — consolidated three-UAV SITL experiment report

## Status

This tool consolidates existing **offline** evidence gates. It has **not** executed PX4, Gazebo or ROS 2. Passing the data gate does not authorize real drone operations, certify autonomous navigation, or prove genuine source provenance.

## Preconditions

Use the Linux PX4/Gazebo runbooks to collect three real PX4 process logs, an observer JSONL containing distinct `uav_1`, `uav_2`, `uav_3` topic streams and actual ROS bag metadata. Create the SHA-256 manifest using `integrations.ros2.capture_manifest`. Maintain raw logs, bag files and a separate source/version audit.

## Run a stationary or preflight-only session

```sh
python3 -m integrations.ros2.experiment_report \
  artifacts/sitl/session/manifest.json \
  --kind stationary --minimum-samples 10 \
  --out artifacts/sitl/stationary-experiment.json
```

## Run a trial where all three vehicles were instructed to move by an independently verified SITL operator

```sh
python3 -m integrations.ros2.experiment_report \
  artifacts/sitl/session/manifest.json \
  --kind movement --minimum-samples 10 \
  --out artifacts/sitl/movement-experiment.json
```

Movement mode requires each vehicle's own local ENU sampled trajectory to exceed provisional displacement and path thresholds. **This repository does not produce the motion commands** and the observer trace is not independent ground truth.

## Result interpretation

- `data_gate_passed`: source-labelled file integrity, telemetry quality, optional local-motion metrics and the advisory supervisor scenario checks.
- `real_sitl_verified`: **always false** in this automatic report; human/independent observation is required.
- `independent_acceptance`: an explicit unresolved checklist for Gazebo models, real PX4 instances, bag contents, actual DDS link interruption, frame alignment and failsafe configuration.
- `supervisor.post_simulated_outage_state=hold` means a four-second silence was injected into offline processing, **not** that an operating PX4 was disconnected.
- `flight_safety_verified`: always false. Cross-vehicle collision geometry is not validated.

For reproducible research, keep raw artifacts, exact version hashes, experiment purpose, operator observations and threshold justifications together. Do not claim a full SITL validation based solely on this JSON report.
