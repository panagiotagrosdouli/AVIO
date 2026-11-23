"""Local read-only telemetry bridge. Never publishes PX4 commands."""
import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
from urllib.parse import urlsplit

VEHICLES = ("uav_1", "uav_2", "uav_3")
FRAME = "vehicle_local_ENU_converted_from_NED_NOT_fleet_aligned"

def normalize_event(event):
    if not isinstance(event, dict) or event.get("vehicle") not in VEHICLES:
        return None
    if event.get("source") != "px4_ros2_observed" or event.get("frame") != FRAME:
        return None
    timestamp = event.get("px4_timestamp_us")
    if type(timestamp) is not int or timestamp < 0:
        return None
    p = event.get("position_m")
    if not isinstance(p, dict):
        return None
    try:
        if any(type(p.get(k)) not in (int, float) for k in ("x", "y", "z")):
            return None
        position = {k: float(p[k]) for k in ("x", "y", "z")}
        if not all(math.isfinite(v) for v in position.values()):
            return None
        received = datetime.fromisoformat(event["received_at"].replace("Z", "+00:00"))
        if received.tzinfo is None:
            return None
    except (ValueError, TypeError, KeyError, OverflowError):
        return None
    return {"vehicle": event["vehicle"], "px4_timestamp_us": timestamp,
            "received_at": received.astimezone(timezone.utc).isoformat(),
            "position_m": position}

def snapshot(path, stale_after_s=3.0, now=None):
    """Read bounded JSONL tail; ignore partial last line and invalid events."""
    if stale_after_s <= 0:
        raise ValueError("stale_after_s must be positive")
    now = now or datetime.now(timezone.utc)
    result = {name: {"state": "missing", "sample": None, "age_s": None}
              for name in VEHICLES}
    path = Path(path)
    if not path.is_file():
        return {"mode": "read_only_local_px4_observer", "status": "no_file",
                "fleet_aligned": False, "vehicles": result}
    limit = 2_000_000
    with path.open("rb") as fh:
        fh.seek(0, 2)
        start = max(0, fh.tell() - limit)
        fh.seek(start)
        raw = fh.read(limit)
    if start:
        _, _, raw = raw.partition(b"\n")
    if not raw.endswith(b"\n"):
        raw = raw.rpartition(b"\n")[0]
    latest = {}
    for line in raw.splitlines():
        if not line or len(line) > 8192:
            continue
        try:
            event = normalize_event(json.loads(line))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if event is not None:
            latest[event["vehicle"]] = event
    for name, event in latest.items():
        age = (now - datetime.fromisoformat(event["received_at"])).total_seconds()
        state = "fresh" if -2 <= age <= stale_after_s else "stale"
        result[name] = {"state": state, "sample": event, "age_s": round(age, 3)}
    return {"mode": "read_only_local_px4_observer",
            "status": "active" if all(v["state"] == "fresh" for v in result.values()) else "degraded",
            "fleet_aligned": False, "cross_vehicle_separation_supported": False,
            "received_at": now.isoformat(), "vehicles": result}

def build_handler(telemetry_path, page_path, stale_after_s=3.0):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            host = self.headers.get("Host", "").split(":")[0].lower()
            if host not in ("localhost", "127.0.0.1"):
                return self.respond(403, b"Forbidden host", "text/plain")
            route = urlsplit(self.path).path
            if route == "/api/snapshot":
                payload = json.dumps(snapshot(telemetry_path, stale_after_s),
                                     allow_nan=False).encode()
                return self.respond(200, payload, "application/json; charset=utf-8")
            if route in ("/", "/mission-control/live.html"):
                return self.respond(200, Path(page_path).read_bytes(), "text/html; charset=utf-8")
            return self.respond(404, b"Not Found", "text/plain")
        def do_POST(self):
            return self.respond(405, b"Read-only endpoint", "text/plain")
        def respond(self, code, data, content_type):
            self.send_response(code)
            for key, value in (("Content-Type", content_type),
                               ("Content-Length", str(len(data))),
                               ("Cache-Control", "no-store"),
                               ("X-Content-Type-Options", "nosniff"),
                               ("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")):
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(data)
    return Handler

def main():
    p = argparse.ArgumentParser(description="AVIO local, read-only telemetry bridge")
    p.add_argument("--input", default="artifacts/sitl/telemetry.jsonl")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--stale-after", type=float, default=3.0)
    args = p.parse_args()
    if not 1 <= args.port <= 65535 or not 0 < args.stale_after <= 300:
        p.error("invalid port or staleness threshold")
    page = Path(__file__).resolve().parents[2] / "mission-control" / "live.html"
    server = ThreadingHTTPServer(("127.0.0.1", args.port),
                                 build_handler(args.input, page, args.stale_after))
    print(f"AVIO read-only: http://127.0.0.1:{args.port}/", flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
