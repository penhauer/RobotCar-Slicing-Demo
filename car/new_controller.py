#!/usr/bin/env python3
import json
import os
import threading
import time
import traceback
from typing import Optional
import subprocess
import urllib.request
import urllib.error

import websocket  # pip install websocket-client
from dotenv import load_dotenv  # pip install python-dotenv

# ---------------- Load .env configuration ----------------
load_dotenv()

WS_SERVER_HOST = os.getenv("WS_SERVER_HOST", "localhost")
WS_SERVER_PORT = int(os.getenv("WS_SERVER_PORT", "8765"))
WS_SCHEME = os.getenv("WS_SCHEME", "ws")
THROTTLE_GAIN = float(os.getenv("THROTTLE_GAIN", "0.2"))
STEERING_OFFSET = float(os.getenv("STEERING_OFFSET", "0.3"))
STATUS_INTERVAL = float(os.getenv("STATUS_INTERVAL", "2.0"))
ENABLE_DISTANCE_SENSOR = os.getenv("ENABLE_DISTANCE_SENSOR", "false").lower() == "true"

# ---------------- Ping feature configuration (new) ----------------
PING_INTERVAL = float(os.getenv("PING_INTERVAL", "1.0"))
ENABLE_PING = os.getenv("ENABLE_PING", "false").lower() == "true"
PING_SERVER_ADDR = os.getenv("PING_SERVER_ADDR", "")
METRIC_SERVER_ADDR = os.getenv("METRIC_SERVER_ADDR", "")

# label config sent with metrics (name/value come from env)
METRIC_LABEL_NAME = os.getenv("METRIC_LABEL_NAME", "source").strip()
METRIC_LABEL_VALUE = os.getenv("METRIC_LABEL_VALUE", "").strip()
if not METRIC_LABEL_NAME:
    METRIC_LABEL_NAME = "source"
if not METRIC_LABEL_VALUE:
    try:
        import socket
        METRIC_LABEL_VALUE = socket.gethostname()
    except Exception:
        METRIC_LABEL_VALUE = "unknown"

# ---------------- Car setup ----------------
car = None
_car_ready = threading.Event()
distance_sensor = None


def start_the_car(throttle_gain=0.2, steering_offset=0.3):
    """Create the NvidiaRacecar and signal readiness."""
    print("Starting the car...")
    try:
        from jetracer.nvidia_racecar import NvidiaRacecar
    except Exception as e:
        print("Failed to import NvidiaRacecar:", e)
        raise

    global car
    car = NvidiaRacecar()
    car.throttle_gain = throttle_gain
    car.steering_offset = steering_offset
    car.steering = 0
    print("Car object successfully created")
    _car_ready.set()


def start_distance_sensor():
    """Initialize and start the distance sensor if enabled."""
    global distance_sensor
    if not ENABLE_DISTANCE_SENSOR:
        print("Distance sensor disabled via config")
        return
        
    try:
        from distance_sensor import DistanceSensor
        distance_sensor = DistanceSensor()
        distance_sensor.start()
        print("Distance sensor initialized")
    except Exception as e:
        print(f"Failed to initialize distance sensor: {e}")
        distance_sensor = None


# ---------------- Ping worker (new) ----------------
class PingWorker:
    def __init__(self, target: str, metric_url: str, interval_s: float = 1.0):
        self.target = target
        self.metric_url = metric_url
        self.interval = interval_s
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        if not self.target:
            print("[Ping] No PING_SERVER_ADDR configured; ping disabled")
            return
        print(f"[Ping] Starting ping worker for target {self.target}, interval {self.interval}s")
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=1.0)

    def _run(self):
        while not self._stop.is_set():
            rtt = self._ping_once(self.target)
            ts_ms = int(time.time() * 1000)
            payload = {
                "type": "ping_rtt",
                "target": self.target,
                "rtt_ms": rtt,
                "ts_ms": ts_ms,
            }
            # attach configured label so metric_server can pick it up
            payload[METRIC_LABEL_NAME] = METRIC_LABEL_VALUE
            try:
                self._send_metric(payload)
            except Exception as e:
                print("[Ping] Failed to send metric:", e)
            time.sleep(self.interval)

    def _ping_once(self, host: str) -> Optional[float]:
        # Use system ping to measure RTT (one probe). Returns milliseconds or None.
        try:
            # -c 1 send one packet, -W 1 timeout 1s (Linux). Adjust if macOS required.
            proc = subprocess.run(
                ["ping", "-c", "1", "-W", "1", host],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=3.0,
            )
            out = str(proc.stdout + proc.stderr)
            if proc.returncode != 0:
                # no reply
                return None
            # look for "time=123.456 ms"
            for part in out.split():
                if part.startswith("time=") and part.endswith("ms"):
                    # part like time=12.345ms or time=12.345 ms (handle both)
                    val = part.replace("time=", "").replace("ms", "")
                    try:
                        return float(val)
                    except Exception:
                        continue
                # handle "time=12.345" with separate "ms"
                if "time=" in part:
                    try:
                        val = part.split("time=")[1].rstrip()
                        if val.endswith("ms"):
                            val = val[:-2]
                        return float(val)
                    except Exception:
                        continue
            # fallback parse: find "time=" anywhere
            idx = out.find("time=")
            if idx != -1:
                tail = out[idx:idx+20]
                import re
                m = re.search(r"time=([0-9\.]+)", tail)
                if m:
                    return float(m.group(1))
            return None
        except Exception as e:
            print(e)
            return None

    def _send_metric(self, payload: dict):
        if not self.metric_url:
            # no metric server configured; just print
            print("[Ping] Metric payload:", payload)
            return

        data = json.dumps(payload).encode("utf-8")
        # Only HTTP(S) transport for metrics (no websocket)
        if self.metric_url.startswith("http://") or self.metric_url.startswith("https://"):
            req = urllib.request.Request(
                self.metric_url, data=data, headers={"Content-Type": "application/json"}, method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    _ = resp.read()  # consume response
            except Exception as e:
                print("[Ping] HTTP metric send failed:", e)
        else:
            # unknown/unsupported scheme — just log the payload
            print("[Ping] Unsupported metric server URL scheme, cannot send:", self.metric_url)
            print(payload)


# ---------------- Control handling ----------------
def control_the_car(d: dict):
    """
    Expected payload from server (newline-delimited JSON), e.g.:
      {"steering": 1, "type": "steering"}
      {"throttle": -1, "type": "throttle"}
    """
    print(d)
    if car is None:
        print("Warning: message received but car is not set")
        return

    try:
        t = d.get("type")
        if t == "steering":
            d["new"] = d["steering"]
            car._on_steering(d)
        elif t == "throttle":
            d["new"] = d["throttle"]
            car._on_throttle(d)
        else:
            raise Exception(f"Unknown command type '{t}'")
    except Exception as e:
        print("Bad control payload:", d)
        traceback.print_exc()


# ---------------- WebSocket client ----------------
class WSClient:
    def __init__(self, url: str, status_interval_s: float = 2.0):
        self.url = url
        self.wsapp: Optional[websocket.WebSocketApp] = None
        self._status_interval_s = status_interval_s
        self._start_ts = time.time()
        self._stop = threading.Event()
        self._connected = threading.Event()
        # Track whether we ever had a successful connection in this client lifetime
        self._had_connection = False

        # Reconnect/backoff settings
        self._reconnect_initial = 1.0
        self._reconnect_max = 10.0

        self._run_thread = threading.Thread(target=self._run_forever, daemon=True)
        self._status_thread = threading.Thread(target=self._status_loop, daemon=True)

    def start(self):
        self._run_thread.start()
        self._status_thread.start()

    def stop(self):
        self._stop.set()
        try:
            if self.wsapp:
                self.wsapp.close()
        except Exception:
            pass
        self._run_thread.join(timeout=1.0)

    # ---- websocket-client callbacks ----
    def _on_open(self, ws):
        print(f"[WS] Connected to {self.url}")
        self._connected.set()
        self._had_connection = True

    def _on_close(self, ws, status_code, msg):
        print(f"[WS] Disconnected ({status_code}): {msg}")
        self._connected.clear()

    def _on_error(self, ws, err):
        print("[WS] Error:", err)

    def _on_message(self, ws, message: str):
        # Handle multiple JSONs in one frame
        lines = message.splitlines() if "\n" in message else [message]
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                control_the_car(d)
            except Exception:
                print("Error decoding incoming payload:", repr(line))
                traceback.print_exc()

    def _run_forever(self):
        retry_delay = self._reconnect_initial
        while not self._stop.is_set():
            try:
                print(f"[WS] Attempting connection to {self.url}")
                self.wsapp = websocket.WebSocketApp(
                    self.url,
                    on_open=self._on_open,
                    on_close=self._on_close,
                    on_error=self._on_error,
                    on_message=self._on_message,
                )
                # This will block until connection closed / error
                self.wsapp.run_forever(ping_interval=10, ping_timeout=5)
            except Exception as e:
                print("[WS] run_forever exception:", e)

            # If stop requested, exit loop
            if self._stop.is_set():
                break

            # Clear wsapp reference (we'll create a new one on next loop)
            self.wsapp = None

            # If we never had a successful connection, use exponential backoff
            if not self._had_connection:
                print(f"[WS] Connection failed, reconnecting in {retry_delay:.1f}s...")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2.0, self._reconnect_max)
                continue

            # If we had a connection before but got disconnected, try quickly
            print("[WS] Connection lost, attempting immediate reconnect...")
            # Reset retry_delay so future connection failures start from initial
            retry_delay = self._reconnect_initial
            # small pause to avoid tight restart loop after graceful disconnects
            time.sleep(1.0)

    def _status_loop(self):
        while not self._stop.is_set():
            if self._connected.is_set() and self.wsapp:
                # Get distance reading if sensor is available
                distance_mm = ""
                if distance_sensor is not None:
                    dist = distance_sensor.get_distance()
                    if dist is not None:
                        distance_mm = dist
                
                payload = {
                    "type": "status",
                    "ts_ms": int(time.time() * 1000),
                    "uptime_s": round(time.time() - self._start_ts, 3),
                    "car_ready": _car_ready.is_set(),
                    "distance_mm": distance_mm,
                }
                try:
                    self.wsapp.send(json.dumps(payload) + "\n")
                except Exception:
                    pass
            time.sleep(self._status_interval_s)


# ---------------- Main ----------------
def main():
    url = f"{WS_SCHEME}://{WS_SERVER_HOST}:{WS_SERVER_PORT}"
    print("Connecting to:", url)

    # Start car on its own thread
    threading.Thread(
        target=start_the_car, args=(THROTTLE_GAIN, STEERING_OFFSET), daemon=True
    ).start()
    
    # Start distance sensor if enabled
    threading.Thread(target=start_distance_sensor, daemon=True).start()

    # Start WebSocket client
    client = WSClient(url, status_interval_s=STATUS_INTERVAL)
    client.start()

    # Start ping worker if enabled
    ping_worker = None
    if ENABLE_PING:
        ping_worker = PingWorker(PING_SERVER_ADDR, METRIC_SERVER_ADDR, interval_s=PING_INTERVAL)
        ping_worker.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        client.stop()
        if distance_sensor:
            distance_sensor.stop()
        if ping_worker:
            ping_worker.stop()


if __name__ == "__main__":
    main()
