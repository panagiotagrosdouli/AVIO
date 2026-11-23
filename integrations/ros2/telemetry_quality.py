"""AVIO telemetry-quality gate for recorded three-UAV PX4 observer JSONL.

Checks sample counts, reception-time span, gaps, NED/ENU provenance, finite XYZ
and individual PX4 timestamp ordering. It cannot authenticate source, establish
synchronized vehicle clocks, or prove successful PX4/Gazebo simulation.
"""
import argparse
from datetime import datetime
import json
import math
from pathlib import Path
from integrations.ros2.live_bridge import normalize_event, VEHICLES

def audit_quality(records, minimum_samples=10, maximum_gap_s=2.5,
                  minimum_span_s=1.0):
    if type(minimum_samples) is not int or minimum_samples < 2:
        raise ValueError("minimum_samples must be an integer >= 2")
    if not all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0
               for v in (maximum_gap_s, minimum_span_s)):
        raise ValueError("invalid temporal thresholds")
    last_px4, last_receive, first_receive = {}, {}, {}
    counts = {name: 0 for name in VEHICLES}
    gaps = {name: 0.0 for name in VEHICLES}
    issues = []
    last_global = None
    for lineno, original in enumerate(records, 1):
        event = normalize_event(original)
        if event is None:
            issues.append(f"line {lineno}: invalid record or provenance")
            continue
        name = event["vehicle"]
        stamp = event["px4_timestamp_us"]
        received = datetime.fromisoformat(event["received_at"])
        if last_global is not None and received < last_global:
            issues.append(f"line {lineno}: reception timestamps out of order")
        last_global = received
        if name in last_px4 and stamp <= last_px4[name]:
            issues.append(f"line {lineno}: {name} PX4 timestamp repeated/reversed")
        if name in last_receive:
            gap = (received - last_receive[name]).total_seconds()
            if gap <= 0:
                issues.append(f"line {lineno}: {name} reception timestamp repeated/reversed")
            elif gap > maximum_gap_s:
                issues.append(f"line {lineno}: {name} reception gap {gap:.3f}s exceeds {maximum_gap_s}s")
            gaps[name] = max(gaps[name], gap)
        else:
            first_receive[name] = received
        last_receive[name] = received
        last_px4[name] = stamp
        counts[name] += 1
    spans = {}
    for name in VEHICLES:
        if counts[name] < minimum_samples:
            issues.append(f"{name}: {counts[name]} samples (minimum {minimum_samples})")
        span = ((last_receive[name] - first_receive[name]).total_seconds()
                if name in first_receive else 0.0)
        spans[name] = round(span, 3)
        if span < minimum_span_s:
            issues.append(f"{name}: receipt span {span:.3f}s < {minimum_span_s}s")
    return {
        "passed": not issues, "scope": "offline observer JSONL quality only",
        "counts": counts, "receive_span_s": spans,
        "max_gap_s": {k: round(v, 3) for k, v in gaps.items()},
        "issues": issues, "shared_reference_frame_verified": False,
        "source_authenticated": False, "gazebo_execution_verified": False
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("recording")
    parser.add_argument("--minimum-samples", type=int, default=10)
    parser.add_argument("--maximum-gap-s", type=float, default=2.5)
    parser.add_argument("--minimum-span-s", type=float, default=1.0)
    parser.add_argument("--out", default="artifacts/sitl/telemetry-quality.json")
    args = parser.parse_args()
    try:
        with Path(args.recording).open(encoding="utf-8") as file:
            records = [json.loads(line) for line in file if line.strip()]
        result = audit_quality(records, args.minimum_samples, args.maximum_gap_s,
                               args.minimum_span_s)
        destination = Path(args.out)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n",
                               encoding="utf-8")
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"Quality gate error: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
