"""Offline evidence of movement in each UAV's *own* PX4 local position frame.

Not a proof of powered flight, common-world coordinates, authenticated source,
Gazebo execution, collision clearance, or autonomous navigation.
"""
import argparse
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from integrations.ros2.live_bridge import normalize_event, VEHICLES
from integrations.ros2.telemetry_quality import audit_quality

def audit_motion(records, *, minimum_samples=10, minimum_displacement_m=0.5,
                 minimum_path_m=0.5, jitter_deadband_m=0.03,
                 maximum_gap_s=2.5, minimum_span_s=1.0):
    """Fail-closed quality and per-vehicle local-position motion test.

    The deadband excludes short single-step jitter from total path length.
    Net displacement is measured first-to-last in each vehicle's *own* frame.
    """
    thresholds=(minimum_displacement_m,minimum_path_m,jitter_deadband_m)
    if any(type(v) not in (int,float) or not math.isfinite(v) or v < 0 for v in thresholds):
        raise ValueError("nonnegative finite motion thresholds required")
    events=list(records)
    quality=audit_quality(events,minimum_samples=minimum_samples,
                          maximum_gap_s=maximum_gap_s,minimum_span_s=minimum_span_s)
    tracks=defaultdict(list)
    for event in events:
        normalized=normalize_event(event)
        if normalized:
            tracks[normalized["vehicle"]].append(normalized)
    vehicles={}
    issues=list(quality["issues"])
    for name in VEHICLES:
        samples=tracks[name]
        if not samples:
            vehicles[name]={"samples":0,"net_displacement_m":None,
                            "deadband_path_length_m":None,"span_s":None,
                            "movement_gate_passed":False}
            issues.append(f"{name}: no valid local-position samples")
            continue
        positions=[tuple(e["position_m"][axis] for axis in ("x","y","z"))
                   for e in samples]
        displacement=math.dist(positions[0],positions[-1])
        length=sum(distance for a,b in zip(positions,positions[1:])
                   if (distance:=math.dist(a,b)) > jitter_deadband_m)
        first=datetime.fromisoformat(samples[0]["received_at"])
        last=datetime.fromisoformat(samples[-1]["received_at"])
        span=(last-first).total_seconds()
        passing=(len(samples)>=minimum_samples
                 and displacement>=minimum_displacement_m
                 and length>=minimum_path_m
                 and span>=minimum_span_s)
        vehicles[name]={
            "samples":len(samples),
            "net_displacement_m":round(displacement,4),
            "deadband_path_length_m":round(length,4),
            "span_s":round(span,4),
            "movement_gate_passed":passing
        }
        if not passing:
            issues.append(f"{name}: local-motion criterion not met")
    return {
        "passed":not issues and quality["passed"]
                 and all(vehicles[v]["movement_gate_passed"] for v in VEHICLES),
        "vehicles":vehicles,
        "telemetry_quality_passed":quality["passed"],
        "issues":issues,
        "thresholds":{"minimum_samples":minimum_samples,
                      "minimum_displacement_m":minimum_displacement_m,
                      "minimum_path_m":minimum_path_m,
                      "jitter_deadband_m":jitter_deadband_m,
                      "maximum_gap_s":maximum_gap_s,
                      "minimum_span_s":minimum_span_s},
        "frame":"independent_per_vehicle_local_ENU_NOT_fleet_aligned",
        "source_authenticated":False,
        "gazebo_execution_verified":False,
        "physical_flight_verified":False,
        "interpretation":"Only recorded local-coordinate variation; not flight validation"
    }

def main():
    parser=argparse.ArgumentParser(description="Audit three-UAV recorded local movement")
    parser.add_argument("recording")
    parser.add_argument("--minimum-samples",type=int,default=10)
    parser.add_argument("--minimum-displacement-m",type=float,default=0.5)
    parser.add_argument("--minimum-path-m",type=float,default=0.5)
    parser.add_argument("--jitter-deadband-m",type=float,default=0.03)
    parser.add_argument("--maximum-gap-s",type=float,default=2.5)
    parser.add_argument("--minimum-span-s",type=float,default=1.0)
    parser.add_argument("--out",default="artifacts/sitl/motion-evidence.json")
    args=parser.parse_args()
    try:
        with Path(args.recording).open(encoding="utf-8") as handle:
            events=[json.loads(line) for line in handle if line.strip()]
        result=audit_motion(events,minimum_samples=args.minimum_samples,
                            minimum_displacement_m=args.minimum_displacement_m,
                            minimum_path_m=args.minimum_path_m,
                            jitter_deadband_m=args.jitter_deadband_m,
                            maximum_gap_s=args.maximum_gap_s,
                            minimum_span_s=args.minimum_span_s)
        destination=Path(args.out)
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    except (OSError,ValueError,TypeError) as exc:
        parser.exit(1,f"Motion evidence audit failed: {exc}\n")
    print(json.dumps(result,indent=2))
    return 0 if result["passed"] else 1

if __name__=="__main__":
    raise SystemExit(main())
