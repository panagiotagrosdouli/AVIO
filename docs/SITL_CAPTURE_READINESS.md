# AVIO — actual three-PX4 SITL capture readiness

This preparation adds prerequisite checks and a manifest generator. **It does not run PX4, launch Gazebo, read real ROS 2 topics or prove a successful three-vehicle simulation.**

## 1. Select a tested toolchain

Choose and record an exact PX4 tag/commit and matching `px4_msgs` definitions. Confirm compatible ROS 2, Gazebo and Micro XRCE-DDS Agent versions in the official PX4 documentation. Current development documentation can differ from tagged releases; avoid unpinned `main` as a reproducible baseline.

- https://docs.px4.io/main/en/ros2/multi_vehicle
- https://docs.px4.io/main/en/middleware/uxrce_dds
- https://docs.px4.io/main/en/sim_gazebo_gz/multi_vehicle_simulation

Do **not** assume topic prefixes: inspect `ros2 topic list` and explicitly configure `PX4_UXRCE_DDS_NS` if default namespace conventions differ by version. AVIO's reader currently assumes `/uav_1` through `/uav_3`; adapt the prefix to the observed graph.

## 2. Check the host

```bash
export PX4_DIR="$HOME/PX4-Autopilot"
source /opt/ros/jazzy/setup.bash
bash scripts/sitl_preflight.sh
```

This stops with nonzero status if key dependencies are unavailable; the script does not install anything.

## 3. Run and record an actual session

Follow `docs/PHASE1B_EXECUTION.md` to launch three PX4 processes and the DDS agent. In a ROS 2 sourced shell:

```bash
python3 -m integrations.ros2.check_topics
python3 -m integrations.ros2.observer --output artifacts/sitl/session/telemetry.jsonl
```

Save the three individual PX4 logs to `artifacts/sitl/session/uav_1.log`, `uav_2.log`, `uav_3.log`. Run `ros2 bag record` for the three observed vehicle-local-position topics and copy its real `metadata.yaml` into the session directory (keep the full rosbag as independent evidence). Verify messages and Gazebo model identities independently.

## 4. Write the evidence manifest and check it

```bash
python3 -m integrations.ros2.capture_manifest artifacts/sitl/session \
  --px4-dir "$HOME/PX4-Autopilot" \
  --px4-msgs-dir "$HOME/ros2_ws/src/px4_msgs" \
  --ros-distro "${ROS_DISTRO}" \
  --gazebo-version "$(gz sim --versions 2>&1 | head -1)" \
  --agent-version "ENTER_INSTALLED_AGENT_VERSION"

python3 -m integrations.ros2.evidence_gate \
  artifacts/sitl/session/manifest.json --minimum-samples 10
```

Replace the agent version placeholder with the actual observed version, and inspect the generated manifest. The manifest does not authenticate versions or file origin. Never label synthetic fixtures as real PX4 capture.

## 5. Independent acceptance review

Review that three actual Gazebo vehicles were present, three distinct PX4 processes were running, the ROS bag contains messages on the intended topics, local positions/clock conventions are consistent with the observation contract, and a deliberate communication interruption yielded the expected supervisory state transition. Passing an offline SHA-256 audit alone is **not** enough to complete Phase 1B.

No aircraft arming, trajectory control, defect detection, collaborative SLAM or hardware deployment is included here.
