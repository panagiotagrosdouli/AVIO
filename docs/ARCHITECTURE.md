# AVIO System Architecture — v0.1

## Implemented data flow
Three-agent deterministic Python kinematic simulation (`avio_mvp`) → versioned `artifacts/latest.json` (positions, frames, observations, alerts) → static read-only Mission Control (`mission-control/index.html`) and `artifacts/inspection-report.md`.

The dashboard does not send flight commands. The scenario contains no real sensor data. Positions are synthetic Cartesian x/y/z in meters, **not** ROS ENU or PX4 NED. Time is simulated seconds from mission start; generation date is metadata.

## Future ROS 2 + PX4 SITL target (unimplemented)
- Launch three PX4 instances in Gazebo with unique MAVLink system IDs and uXRCE-DDS namespaces. Pin tested PX4, Gazebo, ROS 2 and px4_msgs versions.
- ROS 2 telemetry adapter converts vehicle odometry, status and timestamps into versioned mission events; validate ENU/NED and body/world transforms.
- Separate mission scheduler, navigation and operational safety monitoring. Safety limits/geofence/failsafes must be enforced, not merely visualized.
- Image acquisition and camera calibration before defect inference; every observation stores sensor provenance, timestamps, uncertainty and image reference.
- Collaborative perception/map sharing only after isolated baseline and reproducible benchmarks, with explicit license review.
- Authenticated control API considered only after safety and security reviews; Mission Control remains read-only until then.

## Interfaces and safety
Treat `schema_version` as a compatibility contract. Do not connect this simulator to physical UAVs. Separation alerts are post-step checks, not collision avoidance. Synthetic visual checks do not establish defect detection performance.
