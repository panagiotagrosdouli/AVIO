"""Validate provenance and temporal consistency in recorded three-UAV PX4 JSONL.

This is an offline evidence checker, not a flight controller or proof of SITL.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

EXPECTED = ("uav_1", "uav_2", "uav_3")

def verify_records(records, minimum_samples=10):
    if minimum_samples < 1:
        raise ValueError("minimum_samples must be >= 1")
    counts = defaultdict(int)
    last_ts = {}
    issues = []
    for idx, event in enumerate(records, start=1):
        vehicle = event.get("vehicle")
        if vehicle not in EXPECTED:
            issues.append(f"line {idx}: unexpected vehicle")
            continue
        if event.get("source") != "px4_ros2_observed":
            issues.append(f"line {idx}: invalid provenance")
        if event.get("frame") != "vehicle_local_ENU_converted_from_NED_NOT_fleet_aligned":
            issues.append(f"line {idx}: unexpected position frame")
        p = event.get("position_m")
        if not isinstance(p, dict) or not all(
                isinstance(p.get(k), (int, float)) for k in ("x","y","z")):
            issues.append(f"line {idx}: invalid position")
        stamp = event.get("px4_timestamp_us")
        if not isinstance(stamp,int) or isinstance(stamp,bool) or stamp < 0:
            issues.append(f"line {idx}: invalid PX4 timestamp")
        elif vehicle in last_ts and stamp <= last_ts[vehicle]:
            issues.append(f"line {idx}: non-increasing PX4 timestamp for {vehicle}")
        if isinstance(stamp,int) and not isinstance(stamp,bool):
            last_ts[vehicle] = stamp
        counts[vehicle] += 1
    for vehicle in EXPECTED:
        if counts[vehicle] < minimum_samples:
            issues.append(f"{vehicle}: {counts[vehicle]} samples; need {minimum_samples}")
    return {"passed":not issues, "counts":{k:counts[k] for k in EXPECTED},
            "issues":issues, "scope":"offline event-contract gate only"}

def load_jsonl(path):
    with Path(path).open(encoding="utf-8") as fh:
        for idx,line in enumerate(fh,1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid JSON at line {idx}") from exc

def main():
    p=argparse.ArgumentParser()
    p.add_argument("path")
    p.add_argument("--minimum-samples",type=int,default=10)
    args=p.parse_args()
    try:
        report=verify_records(load_jsonl(args.path),args.minimum_samples)
    except (OSError,ValueError,TypeError) as exc:
        print(json.dumps({"passed":False,"error":str(exc)}))
        return 1
    print(json.dumps(report,indent=2))
    return 0 if report["passed"] else 1

if __name__=="__main__":
    raise SystemExit(main())
