#!/usr/bin/env python3
import json
import os
import threading
import time
import traceback
from typing import Optional

import websocket  # pip install websocket-client
from dotenv import load_dotenv  # pip install python-dotenv

# ---------------- Load .env configuration ----------------
load_dotenv()

WS_SERVER_HOST = os.getenv("WS_SERVER_HOST", "localhost")
WS_SERVER_PORT = int(os.getenv("WS_SERVER_PORT", "8765"))
WS_SCHEME = os.getenv("WS_SCHEME", "ws")
THROTTLE_GAIN = float(os.getenv("THROTTLE_GAIN", "0.2"))
STEERING_OFFSET = float(os.getenv("STEERING_OFFSET", "0.3"))
HEALTH_INTERVAL = float(os.getenv("HEALTH_INTERVAL", "2.0"))
ENABLE_DISTANCE_SENSOR = os.getenv("ENABLE_DISTANCE_SENSOR", "false").lower() == "true"

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
        from car.distance_sensor import DistanceSensor
        distance_sensor = DistanceSensor()
        distance_sensor.start()
        print("Distance sensor initialized")
    except Exception as e:
        print(f"Failed to initialize distance sensor: {e}")
        distance_sensor = None


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
            _on_steering(d)
        elif t == "throttle":
            _on_throttle(d)
        else:
            print(f"Unknown command type '{t}'")
    except Exception as e:
        print("Bad control payload:", d)
        traceback.print_exc()


def _on_steering(cmd: dict):
    if hasattr(car, "_on_steering") and callable(car._on_steering):
        car._on_steering(cmd)
        return
    steering = int(cmd.get("steering", 0))
    car.steering = steering
    print(f"[car] steering <- {car.steering}")


def _on_throttle(cmd: dict):
    if hasattr(car, "_on_throttle") and callable(car._on_throttle):
        car._on_throttle(cmd)
        return
    throttle = int(cmd.get("throttle", 0))
    car.throttle = throttle
    print(f"[car] throttle <- {car.throttle}")


# ---------------- WebSocket client ----------------
class WSClient:
    def __init__(self, url: str, health_interval_s: float = 2.0):
        self.url = url
        self.wsapp: Optional[websocket.WebSocketApp] = None
        self._health_interval_s = health_interval_s
        self._start_ts = time.time()
        self._stop = threading.Event()
        self._connected = threading.Event()

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
        while not self._stop.is_set():
            try:
                self.wsapp = websocket.WebSocketApp(
                    self.url,
                    on_open=self._on_open,
                    on_close=self._on_close,
                    on_error=self._on_error,
                    on_message=self._on_message,
                )
                self.wsapp.run_forever(ping_interval=10, ping_timeout=5)
            except Exception as e:
                print("[WS] run_forever exception:", e)

            if self._stop.is_set():
                break
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
                    "type": "health",
                    "ts_ms": int(time.time() * 1000),
                    "uptime_s": round(time.time() - self._start_ts, 3),
                    "car_ready": _car_ready.is_set(),
                    "distance_mm": distance_mm,
                }
                try:
                    self.wsapp.send(json.dumps(payload) + "\n")
                except Exception:
                    pass
            time.sleep(self._health_interval_s)


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
    client = WSClient(url, health_interval_s=HEALTH_INTERVAL)
    client.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        client.stop()
        if distance_sensor:
            distance_sensor.stop()


if __name__ == "__main__":
    main()
