"""AVIO SITL evidence audit. Read-only, offline, conservative.

Validates artifact presence, SHA-256 integrity, three distinct telemetry streams,
and advisory HOLD on simulated interruption. A pass is NOT proof PX4/Gazebo ran.
"""
import argparse
import hashlib
import json
from pathlib import Path
from integrations.ros2.verify_telemetry import verify_records
from integrations.ros2.supervisor_adapter import evaluate_recording
from integrations.ros2.motion_evidence import audit_motion

REQUIRED = ("px4_log_1", "px4_log_2", "px4_log_3", "rosbag_metadata")
HASHED = REQUIRED + ("telemetry_jsonl",)

def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for piece in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(piece)
    return digest.hexdigest()

def audit(manifest_path, minimum_samples=10, require_motion=False):
    path = Path(manifest_path).resolve()
    folder = path.parent
    findings = []
    checks = {}
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"data_gate_passed": False, "findings": [f"manifest: {exc}"],
                "scope": "offline evidence audit; no live PX4 verification"}
    versions = manifest.get("versions", {})
    for field in ("px4_commit", "px4_msgs_commit", "ros_distro", "gazebo_version",
                  "agent_version"):
        if not isinstance(versions.get(field), str) or not versions[field].strip():
            findings.append(f"versions.{field}: missing")
    artifacts = manifest.get("artifacts", {})
    resolved = {}
    for key in HASHED:
        entry = artifacts.get(key)
        if not isinstance(entry, dict):
            findings.append(f"{key}: missing artifact entry")
            continue
        filename, expected = entry.get("path"), entry.get("sha256")
        if not isinstance(filename, str) or not filename:
            findings.append(f"{key}: missing path")
            continue
        target = (folder / filename).resolve()
        if not target.is_relative_to(folder):
            findings.append(f"{key}: path escapes manifest folder")
            continue
        if not target.is_file() or target.stat().st_size == 0:
            findings.append(f"{key}: file absent or empty")
            continue
        if not isinstance(expected, str) or len(expected) != 64:
            findings.append(f"{key}: missing SHA256")
            continue
        actual = sha256_file(target)
        checks[key] = actual == expected.lower()
        if not checks[key]:
            findings.append(f"{key}: SHA256 mismatch")
        else:
            resolved[key] = target
    if "telemetry_jsonl" in resolved:
        events = []
        try:
            with resolved["telemetry_jsonl"].open(encoding="utf-8") as stream:
                for number, line in enumerate(stream, 1):
                    if line.strip():
                        item = json.loads(line)
                        if not isinstance(item, dict):
                            raise ValueError(f"non-object at line {number}")
                        events.append(item)
            # Telemetry must be ordered by reception time, or replay rejects it.
            samples = verify_records(events, minimum_samples)
            checks["telemetry_contract"] = samples["passed"]
            findings.extend(samples["issues"])
            if require_motion:
                movement = audit_motion(events, minimum_samples=max(2, minimum_samples))
                checks["motion_trial"] = movement["passed"]
                if not movement["passed"]:
                    findings.extend("motion: " + issue for issue in movement["issues"])
            if samples["passed"]:
                baseline = evaluate_recording(events, start_advisory=True)
                outage = evaluate_recording(events, start_advisory=True, end_gap_s=4)
                checks["supervisor_reached_running"] = baseline["phase"] == "running"
                checks["outage_to_hold"] = outage["phase"] == "hold"
                checks["no_fake_waypoints"] = not any(outage["completed_waypoints"].values())
                checks["no_automatic_resume"] = not any(
                    "resume" in event["event"] for event in outage["events"])
                for key in ("supervisor_reached_running", "outage_to_hold",
                            "no_fake_waypoints", "no_automatic_resume"):
                    if not checks[key]:
                        findings.append(f"{key}: failed")
        except (ValueError, TypeError, KeyError, OSError) as exc:
            findings.append(f"telemetry processing: {exc}")
    passed = not findings and all(checks.values()) and all(k in checks for k in HASHED)
    return {"data_gate_passed": bool(passed), "checks": checks,
            "findings": findings,
            "scope": "offline file integrity and recorded-stream checks only",
            "requires_independent_review": [
                "three running PX4 SITL instances and distinct Gazebo models",
                "ROS 2 topic type and DDS namespace observations",
                "actual rosbag messages and source-side clock validity",
                "vehicle movement plus operator-induced communications outage",
                "coordinate origin, time synchronization and failsafe behavior"],
            "no_autonomous_flight_claim": True}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--minimum-samples", type=int, default=10)
    parser.add_argument("--report", default="artifacts/sitl/evidence-audit.json")
    parser.add_argument("--require-motion", action="store_true", help="require per-UAV local displacement for a movement trial only")
    args = parser.parse_args()
    if args.minimum_samples < 1:
        parser.error("minimum samples must be >= 1")
    result = audit(args.manifest, args.minimum_samples, require_motion=args.require_motion)
    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["data_gate_passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
