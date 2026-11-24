# AVIO Collaborative Aerial Perception

Independent research direction inspired by [V4RL SkEyes](https://v4rl.com/research/projects351/alias1695542471). No affiliation, shared implementation or validated flight capability is implied.

## Research question
Does exchanging timestamped local occupancy observations among three simulated UAV agents improve exploration coverage under communication delays and sensor noise compared with isolated agents?

## Milestone A: reproducible 2D simulation
- Known simulator ground truth, unknown map for agents; static obstacles and simulated range observations.
- Local occupancy grids with free, occupied and unknown cells; shared coordinate frame assumed initially (not SLAM).
- Compare isolated agents and shared-map agents under identical maps, seeds and sensing budgets.
- Measure coverage, occupancy precision/recall, duplicated observations, communication bytes and mission steps. Report mean and dispersion across at least 20 seeds.
- Explicitly label synthetic observations and distinguish map fusion from actual camera-based perception.

## Milestone B: realism
Introduce pose uncertainty, packet loss and delayed observations; investigate robust fusion and map alignment. Evaluate against ground truth using trajectory error and mapping metrics. Then investigate ROS 2 / PX4 SITL integration and licensed external datasets. Real flights are out of scope until safety and regulatory review.

## First executable baseline
Run `python3 -m avio_mvp.collaborative_perception` from the repository root. The initial experiment uses a synthetic occupancy grid and fixed observation locations, not flight dynamics or autonomous exploration. It compares the information available to a single agent against the shared map, not mission efficiency. Subsequent work must evaluate decentralized and shared planning under equal budgets.
