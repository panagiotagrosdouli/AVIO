# AVIO Phase 1 — three-UAV simulation MVP

**Engineering status:** executable deterministic **kinematic** demonstration. **Not PX4 SITL**, ROS 2, hardware flight software, real camera detection or a flight-safety controller.

## Run locally

Python 3.9+; no dependencies. From repository root:

```sh
python3 -m unittest discover -s tests -v
python3 -m avio_mvp
python3 -m http.server 8000
```

Open http://localhost:8000/mission-control/ . Artifacts are generated at `artifacts/latest.json` and `artifacts/inspection-report.md`. Regenerate after code changes. Dashboard is a read-only recorded mission replay.

## Evidence and limitations

Three uniquely named aircraft; nine uniquely allocated inspection targets; timestamped Cartesian frames; provenance-marked synthetic findings; monitored (but **not enforced**) pairwise separation. One anomaly flag is a test fixture, not a real defect. This prototype has no actual camera, SLAM, physics, obstacle avoidance, ROS 2 or PX4 backend.

See `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, and `docs/RESEARCH.md`. No external academic SLAM code is bundled or represented as AVIO-owned research.
