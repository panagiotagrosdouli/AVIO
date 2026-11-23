# AVIO evidence gates — not claims of deployment readiness

AVIO uses explicit provenance and gated engineering claims.

## Present software checks (CI targets, require verification)
Run `python3 -m unittest discover -s tests -v`, `python3 -m avio_mvp`, `python3 -m avio_mvp.benchmark`. Verify that artifacts contain all nine unique targets and every inspection observation identifies its synthetic source. No result from this suite proves vehicle autonomy.

## Phase 1B: PX4 SITL and ROS 2 gate
Three actual PX4 SITL processes, Gazebo instances/models, unique message topics, aligned timestamps and a recorded demonstration. Do not mark complete from a prepared launch script or read-only observer alone.

## Navigation and coordination gate
Run randomized and adversarial obstacle maps, infeasible routes, crossed trajectories, nonzero uncertainty, emergency stop paths and fault injection. Measure collisions, geofence breaches, minimum 3D separation, recovery success and latency. Current algorithms only plan a grid route and detect conflicts post hoc.

## Perception and SLAM gate
Require calibrated datasets and reproducible splits. Measure inspection precision, recall, false alarms, defect localization and confidence; evaluate ATE/RPE against ground truth for each UAV. Compare distributed and independent baselines, including link loss and limited bandwidth. No inference, localization or map merging is currently implemented.

## Hardware and compliance gate
Complete a hazard analysis, operator procedures, geofencing and failsafe tests, privacy review, local aviation authority requirements, insurance and independent risk assessment before any field trial. Never run real-world UAVs from this prototype.

## Website and commercialization gate
Keep the site factual about simulation status. Do not publish customer results, validated accuracy, deployed fleets, intellectual-property ownership or partnerships without documentation.
