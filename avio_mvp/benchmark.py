"""Machine-readable software-only benchmark (NOT a flight-system benchmark)."""
import argparse
import json
from pathlib import Path
from avio_mvp.__main__ import simulate
from avio_mvp.validation import evaluate_inspection, trajectory_conflicts, plan_grid

def benchmark():
    r = simulate()
    tracks = {n: [(f["vehicles"][n]["x"], f["vehicles"][n]["y"], f["vehicles"][n]["z"])
                  for f in r["frames"]] for n in r["vehicles"]}
    evidence = evaluate_inspection(r)
    alerts = trajectory_conflicts(tracks, 2.0)
    grid_path = plan_grid((0,0),(4,0),{(2,0)},5,5)
    return {"benchmark_version":"1.0",
            "scope":"synthetic software regression; NOT PX4, real physics or safety certification",
            "mission":r["mission_id"], "fleet_size":len(r["vehicles"]),
            "target_count":len(r["targets"]), "coverage_pct":evidence["coverage_pct"],
            "inspection_evidence_passed":evidence["passed"],
            "mission_duration_simulated_s":r["summary"]["duration_s"],
            "sampled_separation_alerts":len(alerts),
            "static_grid_shortest_path_steps":len(grid_path)-1 if grid_path else None,
            "passing":(len(r["vehicles"])==3 and evidence["passed"]
                       and evidence["coverage_pct"]==100 and len(alerts)==0)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="artifacts/benchmark.json")
    args=p.parse_args()
    result=benchmark()
    dst=Path(args.out)
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
    if not result["passing"]:
        raise SystemExit(1)

if __name__=="__main__":
    main()
