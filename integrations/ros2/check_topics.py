"""ROS 2 graph preflight; no PX4 command publication."""
import argparse
import json
import sys
from .observer import topic_for

def audit_topics(observed, prefix="uav"):
    expected = [topic_for(i, prefix) for i in (1, 2, 3)]
    observed_set = set(observed)
    return {"expected": expected, "found": [t for t in expected if t in observed_set],
            "missing": [t for t in expected if t not in observed_set],
            "ready": all(t in observed_set for t in expected)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--namespace-prefix",default="uav")
    args=p.parse_args()
    try:
        import rclpy
    except ImportError as exc:
        raise SystemExit("ROS 2 rclpy is needed: "+str(exc))
    rclpy.init()
    node = rclpy.create_node("avio_topic_preflight")
    try:
        # Graph discovery may need a few spins; avoid assuming empty graph at startup.
        for _ in range(15):
            rclpy.spin_once(node,timeout_sec=0.2)
        graph = node.get_topic_names_and_types()
        report = audit_topics([name for name,_ in graph],args.namespace_prefix)
        types = {name: values for name,values in graph}
        report["unexpected_types"] = {
            topic: types[topic] for topic in report["found"]
            if "px4_msgs/msg/VehicleLocalPosition" not in types[topic]}
        report["ready"] = report["ready"] and not report["unexpected_types"]
        print(json.dumps(report,indent=2))
        return 0 if report["ready"] else 1
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__=="__main__":
    sys.exit(main())
