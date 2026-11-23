"""Combine AVIO offline diagnostics into one reproducible experiment report.

No aircraft-control code; no claim that the source logs are authentic or Gazebo ran.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from integrations.ros2.evidence_gate import audit as audit_bundle
from integrations.ros2.motion_evidence import audit_motion
from integrations.ros2.supervisor_adapter import evaluate_recording
from integrations.ros2.telemetry_quality import audit_quality


def build_experiment_report(manifest_path, *, kind="stationary", minimum_samples=10,
                            maximum_gap_s=2.5, minimum_span_s=1.0):
    if kind not in ("stationary", "movement"):
        raise ValueError("kind must be stationary or movement")
    if type(minimum_samples) is not int or minimum_samples < 2:
        raise ValueError("minimum_samples must be >= 2")
    manifest_path = Path(manifest_path).resolve()
    bundle = audit_bundle(manifest_path, minimum_samples=minimum_samples)
    issues = list(bundle.get("findings", []))
    quality = None
    motion = None
    supervisor = None
    telemetry_path = None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entry = manifest["artifacts"]["telemetry_jsonl"]
        candidate = (manifest_path.parent / entry["path"]).resolve()
        if not candidate.is_relative_to(manifest_path.parent):
            raise ValueError("telemetry path escapes manifest folder")
        # Reject altered data before any further interpretation.
        expected = entry["sha256"]
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError("telemetry SHA-256 missing")
        if hashlib.sha256(candidate.read_bytes()).hexdigest() != expected.lower():
            raise ValueError("telemetry digest mismatch")
        telemetry_path = candidate
        with candidate.open(encoding="utf-8") as stream:
            events = [json.loads(line) for line in stream if line.strip()]
        quality = audit_quality(events, minimum_samples=minimum_samples,
                                maximum_gap_s=maximum_gap_s,
                                minimum_span_s=minimum_span_s)
        if not quality["passed"]:
            issues.extend("quality: " + reason for reason in quality["issues"])
        if kind == "movement":
            motion = audit_motion(events, minimum_samples=minimum_samples,
                                  maximum_gap_s=maximum_gap_s,
                                  minimum_span_s=minimum_span_s)
            if not motion["passed"]:
                issues.extend("motion: " + reason for reason in motion["issues"])
        if quality["passed"]:
            baseline = evaluate_recording(events, start_advisory=True)
            simulated_dropout = evaluate_recording(
                events, start_advisory=True, end_gap_s=4)
            supervisor = {
                "baseline_state": baseline["phase"],
                "post_simulated_outage_state": simulated_dropout["phase"],
                "no_fake_waypoints": not any(simulated_dropout["completed_waypoints"].values()),
                "no_automatic_resume": not any(
                    "resume" in item["event"] for item in simulated_dropout["events"]),
                "outage_is_offline_simulation_only": True
            }
            if baseline["phase"] != "running":
                issues.append("supervisor: baseline was not running")
            if simulated_dropout["phase"] != "hold":
                issues.append("supervisor: simulated outage did not enter hold")
            if not supervisor["no_fake_waypoints"] or not supervisor["no_automatic_resume"]:
                issues.append("supervisor: invalid safety state transition")
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        issues.append("experiment input: " + str(exc))
    # A software data gate passing is deliberately distinct from real SITL verification.
    data_gate = bool(bundle.get("data_gate_passed") and quality is not None
                     and quality["passed"] and
                     (kind != "movement" or (motion is not None and motion["passed"]))
                     and supervisor is not None and not issues)
    return {
        "schema_version": "1.0",
        "experiment": kind,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_manifest": str(manifest_path),
        "telemetry_input_present": telemetry_path is not None,
        "data_gate_passed": data_gate,
        "real_sitl_verified": False,
        "flight_safety_verified": False,
        "px4_command_producer": False,
        "bundle_audit": bundle,
        "telemetry_quality": quality,
        "motion_evidence": motion,
        "supervisor": supervisor,
        "issues": issues,
        "independent_acceptance": {
            "three_px4_instances_observed": "NOT_VERIFIED",
            "three_gazebo_models_observed": "NOT_VERIFIED",
            "rosbag_contents_reviewed": "NOT_VERIFIED",
            "induced_real_dds_outage_observed": "NOT_VERIFIED",
            "coordinate_frames_aligned": "NOT_VERIFIED",
            "px4_failsafe_behavior_reviewed": "NOT_VERIFIED"
        },
        "interpretation": "Data-only evidence audit; external PX4/Gazebo and safety verification required"
    }


def main():
    parser = argparse.ArgumentParser(description="AVIO offline SITL experiment report")
    parser.add_argument("manifest")
    parser.add_argument("--kind", choices=("stationary", "movement"),
                        default="stationary")
    parser.add_argument("--minimum-samples", type=int, default=10)
    parser.add_argument("--maximum-gap-s", type=float, default=2.5)
    parser.add_argument("--minimum-span-s", type=float, default=1.0)
    parser.add_argument("--out", default="artifacts/sitl/experiment-report.json")
    args = parser.parse_args()
    try:
        report = build_experiment_report(
            args.manifest, kind=args.kind, minimum_samples=args.minimum_samples,
            maximum_gap_s=args.maximum_gap_s, minimum_span_s=args.minimum_span_s)
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n",
                        encoding="utf-8")
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"Experiment report failed: {exc}\n")
    print(json.dumps({"data_gate_passed": report["data_gate_passed"],
                      "real_sitl_verified": False,
                      "issues": report["issues"],
                      "report": str(path)}, indent=2))
    return 0 if report["data_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
