#!/usr/bin/env bash
# Preflight only: no flight commands, no package installations, no flight claims.
set -euo pipefail
FAILED=0
check() {
  local tool="$1"
  if command -v "$tool" >/dev/null 2>&1; then
    printf 'OK  %-22s %s\n' "$tool" "$(command -v "$tool")"
  else
    printf 'NO  %-22s missing\n' "$tool"
    FAILED=1
  fi
}
echo "AVIO / PX4 SITL local environment preflight"
check git
check python3
check gz
check ros2
if command -v MicroXRCEAgent >/dev/null 2>&1; then
  echo "OK  DDS agent MicroXRCEAgent"
elif command -v micro-xrce-dds-agent >/dev/null 2>&1; then
  echo "OK  DDS agent micro-xrce-dds-agent"
else
  echo "NO  DDS agent binary (name differs by installation)"
  FAILED=1
fi
if [[ -z "${PX4_DIR:-}" || ! -x "${PX4_DIR}/build/px4_sitl_default/bin/px4" ]]; then
  echo "NO  PX4_DIR/build/px4_sitl_default/bin/px4"
  FAILED=1
else
  echo "OK  PX4 SITL executable at $PX4_DIR"
  git -C "$PX4_DIR" rev-parse HEAD || FAILED=1
fi
if [[ -n "${ROS_DISTRO:-}" ]]; then
  echo "INFO ROS_DISTRO=$ROS_DISTRO (verify the sourced workspace contains matching px4_msgs)"
else
  echo "NO  ROS_DISTRO unset; source ROS 2 environment"
  FAILED=1
fi
echo "Next: run topic preflight separately while three SITL vehicles and DDS agent run."
exit "$FAILED"
