"""Read-only ROS 2 PX4 telemetry observer. Requires installed ROS 2 + matching px4_msgs.

This is an OPTIONAL integration adapter. It does NOT issue commands and has not
been demonstrated against three running PX4 SITL instances in this repository.
"""
import json
import sys
from datetime import datetime, timezone

def ned_to_enu(x_north, y_east, z_down):
    """Position only; orientation conversion is not implemented."""
    return {"x": float(y_east), "y": float(x_north), "z": -float(z_down)}

def main():
    try:
        import rclpy
        from rclpy.node import Node
        from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
        from px4_msgs.msg import VehicleLocalPosition
    except ImportError as exc:
        raise SystemExit("Requires ROS 2 rclpy and PX4-version-matched px4_msgs: " + str(exc))

    class FleetObserver(Node):
        def __init__(self):
            super().__init__("avio_readonly_fleet_observer")
            qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                             durability=DurabilityPolicy.VOLATILE,
                             history=HistoryPolicy.KEEP_LAST, depth=5)
            self.subscriptions = []
            for instance in (1, 2, 3):
                topic = f"/px4_{instance}/fmu/out/vehicle_local_position"
                self.subscriptions.append(self.create_subscription(
                    VehicleLocalPosition, topic,
                    lambda m, i=instance: self.on_position(i, m), qos))
                self.get_logger().info(f"Observing {topic}")
        def on_position(self, instance, msg):
            if not bool(msg.xy_valid and msg.z_valid):
                return
            event = {"schema_version": "1.0", "source": "px4_ros2_observed",
                     "vehicle": f"px4_{instance}", "px4_timestamp_us": int(msg.timestamp),
                     "received_at": datetime.now(timezone.utc).isoformat(),
                     "frame": "ENU_position_converted_from_PX4_NED",
                     "position_m": ned_to_enu(msg.x, msg.y, msg.z)}
            print(json.dumps(event), flush=True)
    rclpy.init(args=sys.argv)
    node = FleetObserver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
