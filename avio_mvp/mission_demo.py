"""Standalone software-only supervisor demonstration. Does NOT control PX4."""
import argparse
import json
from pathlib import Path
from .mission_supervisor import Mission, Observation, VEHICLES

def demo():
    mission = Mission()
    mission.begin_preflight(0.0)
    for name in VEHICLES:
        mission.observe(Observation(name, 0., True, True, (0., 0., 6.)))
    if not mission.check_preflight(0.0) or not mission.start(0.0):
        raise RuntimeError("simulated preflight blocked")
    for waypoint in range(3):
        now = float(waypoint + 1)
        for name in VEHICLES:
            mission.observe(Observation(name, now, True, True, (0., 0., 6.)))
        mission.tick(now)
        for name in VEHICLES:
            mission.waypoint_reached(name, now)
    return mission.report()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="artifacts/mission-supervisor-demo.json")
    args = p.parse_args()
    result = demo()
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{result['phase']}: {sum(result['completed_waypoints'].values())} synthetic waypoint credits")
    if result["phase"] != "completed":
        raise SystemExit(1)

if __name__ == "__main__":
    main()
