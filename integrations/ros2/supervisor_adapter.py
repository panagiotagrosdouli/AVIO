"""Offline, advisory-only PX4 telemetry → AVIO Mission Supervisor adapter.

Only consumes JSONL from AVIO's read-only ROS 2 observer. Does NOT publish to
ROS 2, send commands, infer fleet-wide separation, or credit waypoints.
Reception timestamps are used for offline replay, NOT synchronized PX4 clocks.
"""
import argparse
from datetime import datetime
import json
import math
from pathlib import Path

from avio_mvp.mission_supervisor import Mission, Observation, Phase, VEHICLES
from integrations.ros2.live_bridge import normalize_event

def _elapsed(received, first):
    return (datetime.fromisoformat(received) - first).total_seconds()

def evaluate_recording(records, *, start_advisory=False, stale_after_s=2.0,
                       max_duration_s=300.0, end_gap_s=0.0):
    """Return supervisor evidence without controlling any UAV.

    Records must be ordered by nondecreasing UTC *receipt* time. A gap is
    inspected before accepting the next sample. No automatic resume from HOLD.
    end_gap_s simulates continued absence of messages after final reception.
    """
    if not isinstance(end_gap_s, (int, float)) or not math.isfinite(end_gap_s) or end_gap_s < 0:
        raise ValueError("invalid end_gap_s")
    mission = Mission(stale_after_s=stale_after_s, max_duration_s=max_duration_s)
    mission.begin_preflight(0.0)
    origin = None
    last_time = None
    last_px4 = {}
    accepted = {v: 0 for v in VEHICLES}
    invalid = 0
    for index, record in enumerate(records, 1):
        event = normalize_event(record)
        if event is None:
            invalid += 1
            # Invalid observer evidence is not silently treated as healthy.
            if mission.phase in (Phase.RUNNING, Phase.HOLD):
                mission._set(Phase.HOLD, last_time or 0.0, "invalid_record")
            continue
        stamp = datetime.fromisoformat(event["received_at"])
        if origin is None:
            origin = stamp
        now = _elapsed(event["received_at"], origin)
        if now < 0 or (last_time is not None and now < last_time):
            raise ValueError(f"line {index}: receipt times out of order")
        if last_time is not None and mission.phase in (Phase.RUNNING, Phase.HOLD):
            # Tick slightly before processing a late arrival: never conceal gaps
            # by accepting new telemetry before checking existing data.
            mission.tick(now)
        v = event["vehicle"]
        px4stamp = event["px4_timestamp_us"]
        if px4stamp <= last_px4.get(v, -1):
            invalid += 1
            if mission.phase in (Phase.RUNNING, Phase.HOLD):
                mission._set(Phase.HOLD, now, f"non_monotonic_px4_timestamp:{v}")
            last_time = now
            continue
        last_px4[v] = px4stamp
        pos = event["position_m"]
        mission.observe(Observation(v, now, True, True, (pos["x"], pos["y"], pos["z"])))
        accepted[v] += 1
        if mission.phase == Phase.PREFLIGHT and len(mission.latest) == len(VEHICLES):
            if mission.check_preflight(now) and start_advisory:
                mission.start(now)
        if mission.phase == Phase.RUNNING:
            mission.tick(now)
        last_time = now
    if last_time is not None and end_gap_s and mission.phase in (Phase.RUNNING, Phase.HOLD):
        mission.tick(last_time + end_gap_s)
    report = mission.report()
    report.update({
        "input": "observer_jsonl_unverified_provenance",
        "time_basis": "UTC_receipt_time_relative_to_first_event_not_PX4_clock",
        "fleet_aligned": False, "autonomous_flight": False,
        "waypoint_arrival_detection": False,
        "accepted_samples": accepted, "rejected_samples": invalid,
        "advisory_start_requested": bool(start_advisory),
        "recording_duration_s": round(last_time, 4) if last_time is not None else 0.0,
    })
    return report

def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON line {line_no}") from error
            yield item

def main():
    parser = argparse.ArgumentParser(description="Offline read-only 3-UAV supervisor evaluation")
    parser.add_argument("recording", help="JSONL from integrations.ros2.observer")
    parser.add_argument("--out", default="artifacts/sitl/supervisor-report.json")
    parser.add_argument("--start-advisory", action="store_true",
                        help="evaluate RUNNING advisory state after valid preflight; no PX4 command")
    parser.add_argument("--end-gap", type=float, default=0.0,
                        help="simulate silence after the last received event in seconds")
    args = parser.parse_args()
    try:
        result = evaluate_recording(read_jsonl(args.recording),
                                    start_advisory=args.start_advisory,
                                    end_gap_s=args.end_gap)
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f"Evaluation failed: {error}\n")
    print(f"Advisory supervisor: {result['phase']}; report: {path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
