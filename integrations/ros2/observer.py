"""Read-only ROS 2 PX4 position observer; tested only with synthetic messages.

Requires installed ROS 2 and PX4-version-matched px4_msgs to run.
No command publishing, no vehicle control, no common-origin assertion.
"""
import argparse
import json
from datetime import datetime, timezone

DEFAULT_INSTANCES = (1, 2, 3)

def topic_for(instance, namespace_prefix="uav"):
    """PX4 multi-vehicle default for instances >= 1; PX4_UXRCE_DDS_NS can override."""
    if not isinstance(instance, int) or instance < 1:
        raise ValueError("positive instance index required")
    if not namespace_prefix or not namespace_prefix.replace("_", "").isalnum():
        raise ValueError("invalid namespace prefix")
    return f"/{namespace_prefix}_{instance}/fmu/out/vehicle_local_position"

def ned_to_enu(x_north, y_east, z_down):
    """Position only; orientation and vehicle origin alignment are NOT performed."""
    return {"x": float(y_east), "y": float(x_north), "z": -float(z_down)}

def position_event(instance, msg):
    """Construct a source-labelled, raw-local-frame event from a PX4 message."""
    if not bool(msg.xy_valid and msg.z_valid):
        return None
    return {"schema_version": "1.0", "source": "px4_ros2_observed",
            "vehicle": f"uav_{instance}", "px4_timestamp_us": int(msg.timestamp),
            "received_at": datetime.now(timezone.utc).isoformat(),
            "frame": "vehicle_local_ENU_converted_from_NED_NOT_fleet_aligned",
            "position_m": ned_to_enu(msg.x, msg.y, msg.z)}

def main():
    p = argparse.ArgumentParser(description="Read-only PX4 ROS 2 position observer")
    p.add_argument("--namespace-prefix", default="uav",
                   help="set to match PX4_UXRCE_DDS_NS scheme")
    p.add_argument("--output", default="-", help="append JSONL to file; default stdout")
    args = p.parse_args()
    try:
        import rclpy
        from rclpy.node import Node
        from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
        from px4_msgs.msg import VehicleLocalPosition
    except ImportError as exc:
        raise SystemExit("ROS 2 rclpy and matching px4_msgs required: " + str(exc))

    stream = None
    if args.output != "-":
        stream = open(args.output, "a", encoding="utf-8", buffering=1)
    class FleetObserver(Node):
        def __init__(self):
            super().__init__("avio_readonly_fleet_observer")
            qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                             durability=DurabilityPolicy.VOLATILE,
                             history=HistoryPolicy.KEEP_LAST, depth=5)
            self.subscriptions = []
            self.counts = {i: 0 for i in DEFAULT_INSTANCES}
            for instance in DEFAULT_INSTANCES:
                topic = topic_for(instance, args.namespace_prefix)
                self.subscriptions.append(self.create_subscription(
                    VehicleLocalPosition, topic,
                    lambda msg, i=instance: self.on_position(i, msg), qos))
                self.get_logger().info(f"Observing {topic}")
        def on_position(self, instance, msg):
            event = position_event(instance, msg)
            if event is None:
                return
            self.counts[instance] += 1
            line = json.dumps(event, separators=(",", ":"))
            if stream:
                stream.write(line + "\n")
            else:
                print(line, flush=True)
    rclpy.init()
    node = FleetObserver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info(f"Valid samples per vehicle: {node.counts}")
        node.destroy_node()
        rclpy.shutdown()
        if stream:
            stream.close()

if __name__ == "__main__":
    main()
