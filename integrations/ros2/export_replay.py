"""Convert verified PX4 JSONL into an offline read-only Mission Control replay.

No fusion of independently local PX4 frames. No interpolation, common-origin
assumption, live telemetry transport, inspection observation or flight control.
"""
import argparse
import json
import math
from pathlib import Path
from .verify_telemetry import load_jsonl, verify_records, EXPECTED

SCHEMA_VERSION = "1.0"

def export_replay(records, minimum_samples=10):
    events = list(records)
    audit = verify_records(events, minimum_samples=minimum_samples)
    if not audit["passed"]:
        raise ValueError("telemetry evidence failed: " + "; ".join(audit["issues"]))
    per_vehicle = {name: [] for name in EXPECTED}
    for event in events:
        position = event["position_m"]
        if not all(math.isfinite(float(position[axis])) for axis in ("x", "y", "z")):
            raise ValueError("non-finite coordinate in telemetry")
        per_vehicle[event["vehicle"]].append({
            "timestamp_us": event["px4_timestamp_us"],
            "received_at": event.get("received_at"),
            "position_m": {k: float(position[k]) for k in ("x", "y", "z")}
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "PX4_SITL_recorded_telemetry_unverified_source",
        "provenance": "px4_ros2_observed_JSONL",
        "source_claim": "input asserts PX4 ROS 2 origin; independent SITL verification required",
        "reference_frame": "per_vehicle_local_ENU_not_fleet_aligned",
        "time_alignment": "per_vehicle_px4_timestamps_not_cross_vehicle_synchronized",
        "control": "read_only_replay",
        "has_inspection_observations": False,
        "coverage_pct": None,
        "inter_vehicle_separation_m": None,
        "vehicles": per_vehicle,
        "counts": audit["counts"],
        "evidence_check": audit
    }

def main():
    parser = argparse.ArgumentParser(description="Export offline AVIO PX4 telemetry replay")
    parser.add_argument("input", help="JSONL file recorded by integrations.ros2.observer")
    parser.add_argument("--out", default="artifacts/sitl/replay.json")
    parser.add_argument("--minimum-samples", type=int, default=10)
    args = parser.parse_args()
    try:
        result = export_replay(load_jsonl(args.input), minimum_samples=args.minimum_samples)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"Replay export failed: {exc}\n")
    print(f"Exported {sum(result['counts'].values())} samples to {out}")

if __name__ == "__main__":
    main()
