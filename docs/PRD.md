# AVIO Product Requirements Document — v0.1

Status: Phase 1 engineering simulator. No real prototypes, sensing systems, commercial deployments or field-tested flight autonomy are claimed.

## Problem
Reproducible infrastructure inspection workflow evaluation using multiple simulated UAVs before hardware investment. Initial users: AVIO engineers and technical reviewers.

## MVP acceptance requirements
1. Exactly three independent, uniquely identified UAV agents.
2. Nine distinct fixed inspection targets with unambiguous assignment.
3. Deterministic kinematic trajectories and timestamped telemetry.
4. Pairwise separation monitoring, with violations logged (not avoided).
5. Explicit synthetic observations with source, target, agent, timestamp and finding.
6. Static Mission Control interface with mission replay, state and inspection coverage.
7. Versioned machine-readable evidence and Markdown inspection report.
8. Four automated unit tests and reproducible local run instructions.

Run: `python3 -m unittest discover -s tests -v`; `python3 -m avio_mvp`; `python3 -m http.server 8000`; open `/mission-control/`.

## Nonfunctional constraints
Python standard library for simulator, local-only operation, versioned JSON, no credentials, visible synthetic disclaimers, independent code, no unapproved academic code reuse.

## Excluded
Physics, ROS 2, PX4 SITL, Gazebo, cameras, autonomy stack, collaborative SLAM, dynamic obstacle avoidance, active collision control, field validation, regulatory approval. These require their own milestone and evidence.
