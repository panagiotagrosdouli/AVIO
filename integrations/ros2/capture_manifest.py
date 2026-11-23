"""Capture a transparent manifest for offline SITL evidence checks.

No fabricated versions or files. This only inventories existing local artifacts.
It does not prove that PX4, Gazebo or ROS 2 were running.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ARTIFACTS = {
    "telemetry_jsonl": "telemetry.jsonl",
    "px4_log_1": "uav_1.log",
    "px4_log_2": "uav_2.log",
    "px4_log_3": "uav_3.log",
    "rosbag_metadata": "metadata.yaml",
}

def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def git_commit(path):
    if not path:
        return None
    try:
        value = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--verify", "HEAD"],
            capture_output=True, text=True, check=True, timeout=5
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return value if re.fullmatch(r"[0-9a-fA-F]{40}", value) else None

def build_manifest(directory, versions):
    root = Path(directory)
    assets = {}
    missing = []
    for key, filename in ARTIFACTS.items():
        path = root / filename
        if not path.is_file() or path.stat().st_size == 0:
            missing.append(key)
            continue
        assets[key] = {"path": filename, "sha256": sha256_file(path)}
    required_versions = ("px4_commit", "px4_msgs_commit", "ros_distro",
                         "gazebo_version", "agent_version")
    missing += ["versions." + k for k in required_versions
                if not isinstance(versions.get(k), str) or not versions[k].strip()]
    return {"versions": {k: versions.get(k) for k in required_versions},
            "artifacts": assets,
            "capture_readiness": {"complete": not missing, "missing": missing},
            "provenance_warning": "File hash and Git version are not proof of actual PX4 execution"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", help="session directory with telemetry, PX4 logs, and rosbag metadata")
    parser.add_argument("--px4-dir", help="PX4-Autopilot git working tree")
    parser.add_argument("--px4-msgs-dir", help="px4_msgs git working tree")
    parser.add_argument("--ros-distro", required=True)
    parser.add_argument("--gazebo-version", required=True)
    parser.add_argument("--agent-version", required=True)
    args = parser.parse_args()
    root = Path(args.directory)
    if not root.is_dir():
        parser.error("session directory does not exist")
    versions = {
        "px4_commit": git_commit(args.px4_dir),
        "px4_msgs_commit": git_commit(args.px4_msgs_dir),
        "ros_distro": args.ros_distro, "gazebo_version": args.gazebo_version,
        "agent_version": args.agent_version
    }
    result = build_manifest(root, versions)
    output = root / "manifest.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["capture_readiness"], indent=2))
    return 0 if result["capture_readiness"]["complete"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
