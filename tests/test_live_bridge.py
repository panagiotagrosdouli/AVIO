import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from threading import Thread
from http.server import ThreadingHTTPServer
from integrations.ros2.live_bridge import normalize_event, snapshot, build_handler

NOW = datetime(2026, 11, 23, 20, 0, tzinfo=timezone.utc)
def record(vehicle, received_at=None):
    return {"vehicle":vehicle,"source":"px4_ros2_observed",
            "frame":"vehicle_local_ENU_converted_from_NED_NOT_fleet_aligned",
            "px4_timestamp_us":10,"received_at":(received_at or NOW).isoformat(),
            "position_m":{"x":1.,"y":2.,"z":3.}}

class BridgeTests(unittest.TestCase):
    def test_reject_nonfinite_and_wrong_source(self):
        e=record("uav_1");e["position_m"]["x"]=float("nan")
        self.assertIsNone(normalize_event(e))
        e=record("uav_1");e["source"]="fixture"
        self.assertIsNone(normalize_event(e))
    def test_three_fresh_streams(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"data.jsonl"
            path.write_text("".join(json.dumps(record(v))+"\n" for v in ("uav_1","uav_2","uav_3")))
            result=snapshot(path,now=NOW+timedelta(seconds=1))
            self.assertEqual(result["status"],"active")
            self.assertFalse(result["fleet_aligned"])
    def test_partial_jsonl_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"data.jsonl"
            path.write_bytes((json.dumps(record("uav_1"))+"\n"+json.dumps(record("uav_2"))).encode())
            result=snapshot(path,now=NOW)
            self.assertEqual(result["vehicles"]["uav_1"]["state"],"fresh")
            self.assertEqual(result["vehicles"]["uav_2"]["state"],"missing")
    def test_stale_after_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"data.jsonl"
            path.write_text(json.dumps(record("uav_1"))+"\n")
            self.assertEqual(snapshot(path,now=NOW+timedelta(seconds=5))["vehicles"]["uav_1"]["state"],"stale")
    def test_http_endpoint_rejects_post(self):
        with tempfile.TemporaryDirectory() as tmp:
            page=Path(tmp)/"page.html";page.write_text("<h1>AVIO</h1>")
            server=ThreadingHTTPServer(("127.0.0.1",0),build_handler(Path(tmp)/"missing.jsonl",page,3))
            thread=Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                base=f"http://127.0.0.1:{server.server_address[1]}"
                with urlopen(base+"/api/snapshot",timeout=3) as response:
                    self.assertEqual(json.load(response)["status"],"no_file")
                with self.assertRaises(HTTPError) as caught:
                    urlopen(Request(base+"/api/snapshot",data=b"{}",method="POST"),timeout=3)
                self.assertEqual(caught.exception.code,405)
            finally:
                server.shutdown();server.server_close();thread.join(timeout=3)
if __name__=="__main__":
    unittest.main()
