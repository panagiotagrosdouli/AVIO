"""Three-agent deterministic kinematic inspection demonstration. NOT PX4 SITL."""
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

DRONES = ("uav_01", "uav_02", "uav_03")
TARGETS = [{"id": f"panel_{i*3+j+1:02d}", "x": 4.0 + i*6, "y": 2.0 + j*6}
           for i in range(3) for j in range(3)]

def simulate(step_seconds=1.0, speed=2.0, safe_separation=2.0):
    if min(step_seconds, speed, safe_separation) <= 0:
        raise ValueError("simulation parameters must be positive")
    assignments = {name: TARGETS[i*3:i*3+3] for i, name in enumerate(DRONES)}
    states = {name: {"x": 4.0+i*6, "y": -4.0, "z": 6.0, "next": 0,
                     "status": "active"} for i, name in enumerate(DRONES)}
    frames, observations, alerts = [], [], []
    for tick in range(1000):
        now = round(tick*step_seconds, 3)
        for name in DRONES:
            v = states[name]
            if v["next"] == 3:
                v["status"] = "completed"
                continue
            goal = assignments[name][v["next"]]
            distance = math.hypot(goal["x"]-v["x"], goal["y"]-v["y"])
            movement = min(speed*step_seconds, distance)
            if distance:
                v["x"] += (goal["x"]-v["x"])*movement/distance
                v["y"] += (goal["y"]-v["y"])*movement/distance
            if math.hypot(goal["x"]-v["x"], goal["y"]-v["y"]) < 1e-8:
                observations.append({
                    "target_id": goal["id"], "vehicle_id": name, "time_s": now,
                    "finding": ("review_required" if goal["id"] == "panel_05"
                                else "no_anomaly_simulated"),
                    "source": "deterministic_scenario_fixture"})
                v["next"] += 1
                if v["next"] == 3:
                    v["status"] = "completed"
        positions = {n: {"x": round(states[n]["x"],3), "y": round(states[n]["y"],3),
                         "z": states[n]["z"], "status": states[n]["status"]} for n in DRONES}
        for i, a in enumerate(DRONES):
            for b in DRONES[i+1:]:
                pa, pb = positions[a], positions[b]
                distance = math.dist((pa["x"],pa["y"],pa["z"]), (pb["x"],pb["y"],pb["z"]))
                if distance < safe_separation:
                    alerts.append({"time_s": now, "type": "separation_violation",
                                   "vehicles": [a,b], "distance_m": round(distance,3)})
        frames.append({"time_s": now, "vehicles": positions,
                       "inspected_count": len(observations)})
        if all(states[n]["status"] == "completed" for n in DRONES):
            break
    else:
        raise RuntimeError("simulation step limit exceeded")
    return {
        "schema_version":"1.0", "mission_id":"avio_phase1_three_uav",
        "mode":"deterministic_kinematic_demo_NOT_PX4_SITL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "units":{"position":"m","time":"s"}, "vehicles":list(DRONES),
        "targets":TARGETS, "frames":frames, "observations":observations,
        "allocations":{n:[t["id"] for t in assignments[n]] for n in DRONES},
        "alerts":alerts, "summary":{
            "status":"completed", "inspected":len(observations),
            "total_targets":len(TARGETS), "coverage_pct":100.0*len(observations)/len(TARGETS),
            "review_required":sum(o["finding"]=="review_required" for o in observations),
            "separation_violations":len(alerts),"duration_s":frames[-1]["time_s"]}}

def write_artifacts(result, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory/"latest.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    s = result["summary"]
    lines = ["# AVIO simulated inspection report", "",
             "**SYNTHETIC ONLY — not real inspection, sensor detection or PX4 SITL.**", "",
             f"Coverage: {s['inspected']}/{s['total_targets']} ({s['coverage_pct']:.1f}%)",
             f"Duration: {s['duration_s']} s",
             f"Separation alerts (monitoring only): {s['separation_violations']}", "",
             "| Target | Vehicle | Finding | Provenance |", "|---|---|---|---|"]
    lines.extend(f"| {o['target_id']} | {o['vehicle_id']} | {o['finding']} | {o['source']} |"
                 for o in result["observations"])
    lines += ["", "No physics, sensors, SLAM, obstacle avoidance, or enforced collision avoidance.",
              "Review flags are fixtures and must not inform real infrastructure decisions."]
    (directory/"inspection-report.md").write_text("\n".join(lines)+"\n", encoding="utf-8")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="artifacts")
    args = p.parse_args()
    result = simulate()
    write_artifacts(result,args.out)
    print("SIMULATION ONLY:",result["summary"])
