# Multi-vehicle PX4 SITL integration runbook — unvalidated

**Status:** manual integration instructions and a read-only ROS 2 observer. **No claim that PX4 SITL was installed or run for AVIO.** Do not use for physical flight.

## Host and versions
Use Ubuntu 24.04, ROS 2 Jazzy, and the PX4-supported Gazebo release. Pin a single PX4-Autopilot release/tag plus the corresponding `px4_msgs` branch or commit before running. Do not mix PX4 `main` with arbitrary `px4_msgs` without checking message compatibility. Install PX4 SITL, Gazebo, the uXRCE-DDS agent, ROS 2, and colcon following authoritative PX4 documentation.

## Launch — verify against pinned PX4 release
In the PX4-Autopilot repository, build `make px4_sitl`. Start Gazebo with the first vehicle (example supported by the PX4 multi-vehicle documentation):

```bash
PX4_SYS_AUTOSTART=4001 PX4_GZ_MODEL_POSE="0,0" PX4_SIM_MODEL=gz_x500 ./build/px4_sitl_default/bin/px4 -i 1
```

For additional vehicles in separate terminals while Gazebo runs, use equivalent commands with `-i 2` and `-i 3`, spawn poses such as `"0,5"` and `"0,10"`, and the `PX4_GZ_STANDALONE=1` variable when reusing the running world. These are templates that depend on PX4 release and local Gazebo setup.

In a separate terminal run the uXRCE-DDS agent (per the installed PX4 docs, typically UDP port 8888). Confirm that the ROS 2 graph exposes three namespaces and the topic `/px4_1/fmu/out/vehicle_local_position`, `/px4_2/fmu/out/vehicle_local_position`, `/px4_3/fmu/out/vehicle_local_position`. Namespace assignment is release dependent: inspect `PX4_UXRCE_DDS_NS` and the PX4 multi-vehicle documentation.

```bash
source /opt/ros/jazzy/setup.bash
# Source your overlay containing a matching px4_msgs package.
ros2 topic list | grep vehicle_local_position
python3 -m integrations.ros2.observer
```

Observer prints one JSON event per valid local-position message and has **no command publisher**. PX4 local origins can differ among vehicles: do not compare cross-vehicle positions or separation without proving a common reference frame and time alignment. The prototype browser dashboard does not consume these events yet.

## Exit criteria for verified Phase 1B
- Record exact Git SHAs, binary versions, OS, Gazebo version, setup logs and namespace mapping.
- Demonstrate three simultaneously running PX4 instances with unique vehicle identity and telemetry topics.
- Validate position conversion, timestamps, local origin alignment and actual movement from each vehicle.
- Save a short rosbag and a reproducible launch script; introduce automated smoke tests.
- Demonstrate independent control with PX4 offboard requirements and failsafes **only in SITL** following safety review.

## Source references
- https://docs.px4.io/main/en/ros2/multi_vehicle
- https://docs.px4.io/main/en/sim_gazebo_gz/multi_vehicle_simulation
- https://docs.px4.io/main/en/ros2/user_guide
- https://docs.px4.io/main/en/middleware/uxrce_dds
