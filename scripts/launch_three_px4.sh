#!/usr/bin/env bash
# AVIO three-instance PX4/Gazebo launch template; Linux SITL ONLY.
# --dry-run prints the exact intended commands without requiring PX4/Gazebo.
# No vehicle arming, mode switching, takeoff, or position setpoints.
set -euo pipefail

DRY_RUN=0
STARTUP_DELAY="${AVIO_STARTUP_DELAY_SECONDS:-5}"
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi
if [[ $# -ne 0 ]]; then
  echo "Usage: PX4_DIR=/path/to/PX4-Autopilot bash scripts/launch_three_px4.sh [--dry-run]" >&2
  exit 2
fi
if [[ ! "$STARTUP_DELAY" =~ ^[0-9]+$ ]]; then
  echo "AVIO_STARTUP_DELAY_SECONDS must be a nonnegative integer" >&2
  exit 2
fi

PX4_DIR="${PX4_DIR:-$HOME/PX4-Autopilot}"
BIN="$PX4_DIR/build/px4_sitl_default/bin/px4"
OUT="${AVIO_SITL_LOG_DIR:-$PWD/artifacts/sitl}"
# Resolve relative log location BEFORE changing into PX4's working directory.
if [[ "$OUT" != /* ]]; then OUT="$PWD/$OUT"; fi

if (( DRY_RUN )); then
  printf '%s\n' "AVIO PX4 SITL LAUNCH PLAN — NOT EXECUTED" "PX4 binary: $BIN" "Logs: $OUT"
  for i in 1 2 3; do
    y=$(( (i - 1) * 5 ))
    args=(PX4_SYS_AUTOSTART=4001 PX4_SIM_MODEL=gz_x500 "PX4_GZ_MODEL_POSE=0,${y}")
    if (( i > 1 )); then args+=(PX4_GZ_STANDALONE=1); fi
    printf 'uav_%d: ' "$i"
    printf '%q ' env "${args[@]}" "$BIN" -i "$i"
    printf '> %q 2>&1\n' "$OUT/uav_${i}.log"
  done
  exit 0
fi

[[ -x "$BIN" ]] || { echo "Missing PX4 SITL binary: $BIN (run make px4_sitl)" >&2; exit 2; }
command -v gz >/dev/null 2>&1 || { echo "Gazebo CLI not found: gz" >&2; exit 2; }
mkdir -p "$OUT"
PIDS=()
cleanup() {
  trap - INT TERM EXIT
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  for pid in "${PIDS[@]}"; do wait "$pid" 2>/dev/null || true; done
}
trap cleanup INT TERM EXIT
cd "$PX4_DIR"
echo "Starting PX4 SITL vehicles 1/2/3. Logs in $OUT"
for i in 1 2 3; do
  y=$(( (i - 1) * 5 ))
  args=(PX4_SYS_AUTOSTART=4001 PX4_SIM_MODEL=gz_x500 "PX4_GZ_MODEL_POSE=0,${y}")
  if (( i > 1 )); then args+=(PX4_GZ_STANDALONE=1); fi
  env "${args[@]}" "$BIN" -i "$i" >"$OUT/uav_${i}.log" 2>&1 &
  pid=$!
  PIDS+=("$pid")
  sleep "$STARTUP_DELAY"
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "PX4 instance $i exited during startup; inspect $OUT/uav_${i}.log" >&2
    exit 1
  fi
  echo "Instance $i process alive (PID $pid), but NOT validated as active in Gazebo"
done
echo "Start MicroXRCEAgent separately and run ROS 2 topic/telemetry checks."
echo "Expected default PX4 ROS 2 topic prefixes: /uav_1 /uav_2 /uav_3"
echo "Press Ctrl+C to terminate the three launched PX4 processes."
# Wait for each vehicle so failures cannot be hidden by a successful last child.
result=0
for pid in "${PIDS[@]}"; do
  wait "$pid" || result=1
done
if (( result != 0 )); then
  echo "At least one PX4 instance exited abnormally; inspect SITL logs." >&2
fi
exit "$result"
