#!/usr/bin/env bash
# AVIO manual SITL launcher. Requires a previously built and version-pinned PX4 tree.
# Run from AVIO root: PX4_DIR=/path/to/PX4-Autopilot bash scripts/launch_three_px4.sh
set -euo pipefail
: "${PX4_DIR:?Set PX4_DIR to a built PX4-Autopilot checkout}"
BIN="$PX4_DIR/build/px4_sitl_default/bin/px4"
[[ -x "$BIN" ]] || { echo "Missing $BIN; build with make px4_sitl" >&2; exit 2; }
command -v gz >/dev/null || { echo "Gazebo 'gz' not on PATH" >&2; exit 2; }
OUT="${AVIO_SITL_LOG_DIR:-$PWD/artifacts/sitl}"
mkdir -p "$OUT"
PIDS=()
stop_all() {
  trap - INT TERM EXIT
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap stop_all INT TERM EXIT
cd "$PX4_DIR"
echo "Launching three PX4 SITL instances; logs: $OUT"
# Instance 1 starts Gazebo; instances 2/3 attach as standalone clients.
for i in 1 2 3; do
  x=$(( (i - 1) * 5 ))
  if [[ $i -eq 1 ]]; then
    env PX4_SYS_AUTOSTART=4001 PX4_GZ_MODEL_POSE="0,0" \
      PX4_SIM_MODEL=gz_x500 "$BIN" -i "$i" >"$OUT/uav_${i}.log" 2>&1 &
  else
    env PX4_GZ_STANDALONE=1 PX4_SYS_AUTOSTART=4001 \
      PX4_GZ_MODEL_POSE="0,${x}" PX4_SIM_MODEL=gz_x500 \
      "$BIN" -i "$i" >"$OUT/uav_${i}.log" 2>&1 &
  fi
  PIDS+=("$!")
  sleep 5
  kill -0 "${PIDS[-1]}" 2>/dev/null || { echo "Instance $i exited; inspect logs" >&2; exit 1; }
done
printf '%s\n' "Processes launched. Separately start MicroXRCEAgent udp4 -p 8888 and ROS 2 observer."
printf '%s\n' "Default namespaces for instances 1-3: /uav_1, /uav_2, /uav_3"
echo "Press Ctrl+C to terminate all three PX4 processes."
wait
