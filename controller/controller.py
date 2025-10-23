#!/usr/bin/env python3
import json
import keyboard
import logging
import os
import socket
import threading
import time
from websocket_server import WebsocketServer
from dotenv import load_dotenv



# ==============================
# Load configuration from .env
# ==============================
load_dotenv()

WS_HOST = os.getenv("WS_HOST", "0.0.0.0")
WS_CONTROL_PORT = int(os.getenv("WS_CONTROL_PORT", "8765"))
STREAMING_PORT = int(os.getenv("STREAMING_PORT", "8554"))
PROCESS_VIDEO = os.getenv("PROCESS_VIDEO", "false").lower() == "true"
PROCESS_DISTANCE = os.getenv("PROCESS_DISTANCE", "false").lower() == "true"
DISTANCE_THRESHOLD = int(os.getenv("DISTANCE_THRESHOLD", "30"))


# ==============================
# Non-async WebSocket "push" server
# ==============================

class ClientSocket:
    def __init__(self, server_ip: str, server_port: int) -> None:
        host = server_ip
        port = server_port
        self._clients_lock = threading.Lock()
        self._client = None

        self.server = WebsocketServer(port=port, host=host, loglevel=logging.WARNING)
        self.server.set_fn_new_client(self._on_new_client)
        self.server.set_fn_client_left(self._on_client_left)
        self.server.set_fn_message_received(self._on_message_received)  # added message handler

        self._thread = threading.Thread(target=self.server.run_forever, daemon=True)
        self._thread.start()

        self.distance_handler = None 

        pretty_host = self._pretty_host(host)
        print(f"[WS] Listening on ws://{pretty_host}:{port}")

    def _on_new_client(self, client, server):
        addr = client.get('address')
        print(f"[WS] Client connected: {addr[0]}:{addr[1]}")
        with self._clients_lock:
            self._client = client

    def _on_client_left(self, client, server):
        addr = client.get('address')
        print(f"[WS] Client disconnected: {addr[0]}:{addr[1]}")
        with self._clients_lock:
            if self._client is client:
                self._client = None

    def send(self, msg):
        payload = json.dumps(msg) + "\n"
        with self._clients_lock:
            if not self._client:
                # No client connected, ignore message
                return
            client = self._client
        
        try:
            self.server.send_message(client, payload)
        except Exception:
            # Send failed, ignore message
            pass

    def close(self):
        try:
            if hasattr(self.server, "shutdown_gracefully"):
                self.server.shutdown_gracefully()
            else:
                self.server._stop = True
        except Exception:
            pass
        self._thread.join(timeout=1.0)

    def _pretty_host(self, host: str) -> str:
        if host in ("0.0.0.0", "", None):
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return "localhost"
        return host

    def _on_message_received(self, client, server, message):
        """Handle incoming messages (newline-delimited JSON) from car controller."""
        try:
            lines = message.splitlines() if "\n" in message else [message]
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                msg_type = data.get("type")
                if msg_type == "status":
                    self._handle_status_message(data)
                else:
                    print(f"[WS] Received message: {data}")
        except json.JSONDecodeError as e:
            print(f"[WS] Failed to parse message: {e}")
        except Exception as e:
            print(f"[WS] Error handling message: {e}")

    def _handle_status_message(self, data: dict):
        """Process and display status information from the car."""
        uptime = data.get("uptime_s", 0)
        car_ready = data.get("car_ready", False)
        distance_mm = data.get("distance_mm", "")
        
        status_parts = [f"Car ready: {car_ready}", f"Uptime: {uptime}s"]
        
        if distance_mm != "":
            distance_cm = distance_mm / 10.0
            status_parts.append(f"Distance: {distance_mm}mm ({distance_cm:.1f}cm)")
            if not self.distance_handler is None:
                self.distance_handler.handle_distance_report(distance_cm)
            
        print(f"[Status] {' | '.join(status_parts)}")
        print("\n\n")


    def register_distance_report_handler(self, distance_handler):
        self.distance_handler = distance_handler



# ==============================
# Keyboard controller
# ==============================
class Controller:
    def __init__(self, client_socket: ClientSocket):
        self.client_socket = client_socket
        self.steering = 0
        self.throttle = 0
        self.auto_mode = False
        self._lock = threading.Lock()
        
    def set_auto_mode(self, enabled):
        """Enable or disable auto mode."""
        with self._lock:
            self.auto_mode = enabled
            if enabled:
                print("enabled")
                self.throttle = 1
                self._send_control('throttle', 1)
            else:
                print("disabled")
                self.throttle = 0
                self._send_control('throttle', 0)
    
    def update_axes(self, steering, throttle):
        """Update both steering and throttle atomically."""
        with self._lock:
            if self.steering != steering:
                self.steering = steering
                self._send_control('steering', steering)
            if self.throttle != throttle:
                self.throttle = throttle
                self._send_control('throttle', throttle)
    
    def _send_control(self, control_type, value):
        """Send control message, ignore if send fails."""
        msg = {
            'type': control_type,
            control_type: value
        }
        self.client_socket.send(msg)
    
    def stop(self):
        """Stop all movement."""
        self.update_axes(0, 0)


class KeyboardController:
    """Keyboard input handler using the `keyboard` module (W/A/S/D, M auto, Q quit)."""

    def __init__(self, controller: Controller):
        self.controller = controller
        self.keyboard_thread = threading.Thread(target=self.keyboard_listener, daemon=True)
        self.keyboard_thread.start()

    def keyboard_listener(self):
        print(
            """
[keyboard] Listening for inputs.
Use W/A/S/D for control, M for auto-forward, Q to quit.
            """
        )

        running = True
        auto = False
        SEND = 0.05
        last_send = 0.0
        last_pressed = 0

        try:
            while running:
                if auto:
                    if len(keyboard._pressed_events) > 0 and time.monotonic() - last_pressed > 0.3:
                        auto = False

                    if not self.controller.auto_mode:
                        auto = False
                        t = 0
                else:
                    if keyboard.is_pressed('w'):
                        t = 1
                        last_pressed = time.monotonic()
                    elif keyboard.is_pressed('s'):
                        t = -1
                        last_pressed = time.monotonic()
                    else:
                        t = 0

                    if keyboard.is_pressed('a'):
                        s = -1
                        last_pressed = time.monotonic()
                    elif keyboard.is_pressed('d'):
                        s = 1
                        last_pressed = time.monotonic()
                    else:
                        s = 0

                    if keyboard.is_pressed('m'):
                        last_pressed = time.monotonic()
                        t = 0.9
                        auto = True
                        self.controller.set_auto_mode(True)

                # Quit
                if keyboard.is_pressed('q'):
                    self.controller.stop()
                    running = False
                    break

                # if auto and not self.controller.auto_mode: # DistanceHandler says stop
                #     auto = False
                #     self.controller.set_auto_mode(False)

                # stop_auto = False
                # Auto mode: set when M is pressed; cancel on manual input

                
                # if auto and stop_auto:
                #     auto = False
                #     self.controller.set_auto_mode(False)


                # Send at fixed rate
                # now = time.monotonic()
                # if (now - last_send) >= SEND:
                #     last_send = now
                self.controller.update_axes(s, t)
                time.sleep(0.05)
        finally:
            print("calling stop")
            self.controller.stop()
            print("[keyboard] Listener exit.")


class DistanceController:
    def __init__(self, controller: Controller):
        self.controller = controller

    def handle_distance_report(self, distance_cm: int):
        if not PROCESS_DISTANCE:
            return
        print("Received distance ", distance_cm, self.threshold, PROCESS_DISTANCE, controller.auto_mode)
        if distance_cm < DISTANCE_THRESHOLD and controller.auto_mode:
            self.stop_auto_move()
    
    def stop_auto_move(self):
        self.controller.set_auto_mode(False)



# ==============================
# Main
# ==============================
if __name__ == "__main__":
    print(f"WebSocket: ws://{WS_HOST}:{WS_CONTROL_PORT}")
    print(f"Streaming port: {STREAMING_PORT} | Process Video: {PROCESS_VIDEO}")

    client_socket = ClientSocket(server_ip=WS_HOST, server_port=WS_CONTROL_PORT)
    controller = Controller(client_socket)
    dc = DistanceController(controller)
    client_socket.register_distance_report_handler(dc)
    client = KeyboardController(controller)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        client_socket.close()  # fixed incomplete call
