#!/usr/bin/env python3
import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
import tty
import termios
import select
import os
import sys
import tty
import termios
import select
import threading
import time
import traitlets
import subprocess

# from video_processing import capture_thread, command_dict

import traitlets
from websocket_server import WebsocketServer
from dotenv import load_dotenv  # pip install python-dotenv

# from video_processing import capture_thread, command_dict


# ==============================
# Load configuration from .env
# ==============================
load_dotenv()

WS_HOST = os.getenv("WS_HOST", "0.0.0.0")
WS_CONTROL_PORT = int(os.getenv("WS_CONTROL_PORT", "8765"))
STREAMING_PORT = int(os.getenv("STREAMING_PORT", "8554"))
PROCESS_VIDEO = os.getenv("PROCESS_VIDEO", "false").lower() == "true"


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
                raise RuntimeError("No WebSocket client connected")
            client = self._client
        self.server.send_message(client, payload)

    def send_twice(self, msg):
        try:
            self.send(msg)
        except Exception as e:
            print("Send failed. Will retry once.", e)
            time.sleep(0.1)
            try:
                self.send(msg)
            except Exception as e2:
                print("Second send failed; dropping message.", e2)

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
                if msg_type == "health":
                    self._handle_health_message(data)
                else:
                    print(f"[WS] Received message: {data}")
        except json.JSONDecodeError as e:
            print(f"[WS] Failed to parse message: {e}")
        except Exception as e:
            print(f"[WS] Error handling message: {e}")

    def _handle_health_message(self, data: dict):
        """Process and display health/status information from the car."""
        uptime = data.get("uptime_s", 0)
        car_ready = data.get("car_ready", False)
        distance_mm = data.get("distance_mm", "")
        
        status_parts = [f"Car ready: {car_ready}", f"Uptime: {uptime}s"]
        
        if distance_mm != "":
            distance_cm = distance_mm / 10.0
            status_parts.append(f"Distance: {distance_mm}mm ({distance_cm:.1f}cm)")
            
        print(f"[Health] {' | '.join(status_parts)}")





# ==============================
# Keyboard controller
# ==============================
import os, re, sys, time, select, subprocess, shutil, threading, subprocess, termios, tty
import traitlets

class KeyboardController(traitlets.HasTraits):
    steering = traitlets.Int()
    throttle = traitlets.Int()
    change = traitlets.Dict()

    # --- helpers (nested) ---
    class _KeyState:
        def __init__(self): self.down = set()
        def set_down(self, k): self.down.add(k)
        def set_up(self, k): self.down.discard(k)
        def is_down(self, k): return k in self.down

    class _RawTTY:
        def __enter__(self):
            self.is_tty = sys.stdin.isatty()
            if self.is_tty:
                self.fd = sys.stdin.fileno()
                self.old = termios.tcgetattr(self.fd)
                tty.setraw(self.fd)
            return self
        def __exit__(self, *a):
            if getattr(self, 'is_tty', False):
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)

    # scancodes -> keys (Linux set 1; adjust if needed)
    _SC_TO_KEY = {
        0x11: 'w',  # W
        0x1E: 'a',  # A
        0x1F: 's',  # S
        0x20: 'd',  # D
        0x32: 'm',  # M
        0x10: 'q',  # Q
    }
    _MAKE_RE  = re.compile(r"^0x([0-9a-f]+)\+\s*$", re.I)
    _BREAK_RE = re.compile(r"^0x([0-9a-f]+)-\s*$", re.I)

    @traitlets.validate('change')
    def _clip_change(self, proposal):
        return proposal['value']

    def __init__(self, client_socket):
        self.client_socket = client_socket
        self.setup_trait_links()

        self.keyboard_thread = threading.Thread(target=self.keyboard_listener)
        self.keyboard_thread.daemon = True
        self.keyboard_thread.start()

    # --- trait plumbing ---
    def setup_trait_links(self):
        traitlets.dlink((self, 'steering'), (self, 'change'), transform=self._update_steering)
        traitlets.dlink((self, 'throttle'), (self, 'change'), transform=self._update_throttle)

    def _update_steering(self, value):
        c = self.change.copy()
        c['steering'] = value
        c['type'] = 'steering'
        return c

    def _update_throttle(self, value):
        c = self.change.copy()
        c['throttle'] = value
        c['type'] = 'throttle'
        return c

    @traitlets.observe('change')
    def _on_change(self, d):
        msg = {'new': d['new']}
        try:
            self.client_socket.send_twice(msg)
        except Exception as e:
            print("Send failed with error.")
            print(e)

    # --- public entry ---
    def keyboard_listener(self):
        # prefer kbd/showkey; fallback to raw stdin
        if self._usable_showkey() and self._on_real_vt():
            self._keyboard_listener_kbd()
        else:
            self._keyboard_listener_stdin()

    # --- impl: KBD/showkey path ---
    def _keyboard_listener_kbd(self):
        print("[kbd] Using `showkey --scancodes` (Linux VT). Keys: W/A/S/D, M auto, Q quit.")
        ks = self._KeyState()
        auto = False
        send_dt = 0.05
        last_send = 0.0

        proc = subprocess.Popen(
            ["showkey", "--scancodes"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,
            bufsize=0,
        )

        try:
            while True:
                # non-blocking read of stdout
                fd = proc.stdout.fileno()
                r, _, _ = select.select([fd], [], [], 0.02)
                if r:
                    chunk = os.read(fd, 4096)
                    if not chunk:
                        break
                    for line in chunk.decode(errors="ignore").splitlines():
                        m = self._MAKE_RE.match(line) or self._BREAK_RE.match(line)
                        if not m:
                            continue
                        code = int(m.group(1), 16)
                        key = self._SC_TO_KEY.get(code)
                        if not key:
                            continue
                        if line.endswith('+'):
                            ks.set_down(key)
                            if key == 'm': auto = True
                            if key == 'q':
                                self._apply_axes(0, 0)
                                proc.terminate()
                                proc.wait(timeout=1)
                                return
                        else:
                            ks.set_up(key)

                # auto cancels if manual input occurs
                if auto and any(ks.is_down(k) for k in ('w','a','s','d','q')):
                    auto = False

                # periodic send
                now = time.monotonic()
                if (now - last_send) >= send_dt:
                    last_send = now
                    t = 1 if ks.is_down('w') else (-1 if ks.is_down('s') else 0)
                    s = -1 if ks.is_down('a') else (1 if ks.is_down('d') else 0)
                    if ks.is_down('w') and ks.is_down('s'): t = 0
                    if ks.is_down('a') and ks.is_down('d'): s = 0
                    if auto: t = 1
                    self._apply_axes(s, t)

                if proc.poll() is not None:
                    break
        finally:
            try:
                if proc.poll() is None:
                    proc.terminate()
                    try: proc.wait(timeout=1)
                    except subprocess.TimeoutExpired: proc.kill()
            finally:
                self._apply_axes(0, 0)
                print("[kbd] Listener exit.")

    # --- impl: raw-stdin fallback ---
    def _keyboard_listener_stdin(self):
        print("[stdin] Raw-mode fallback. Keys: W/A/S/D, M auto, Q quit. (run with -it for TTY)")
        pressed, last_seen = set(), {}
        auto = False
        RELEASE_MS = 120
        POLL = 0.01
        SEND = 0.05
        last_send = 0.0

        def sweep():
            now = time.monotonic() * 1000
            for k, t in list(last_seen.items()):
                if now - t > RELEASE_MS:
                    pressed.discard(k)

        try:
            with self._RawTTY():
                while True:
                    r, _, _ = select.select([sys.stdin], [], [], POLL)
                    if r:
                        data = sys.stdin.buffer.read1(1024) if hasattr(sys.stdin, "buffer") else sys.stdin.read(1)
                        if not data:
                            break
                        if isinstance(data, str):
                            data = data.encode()
                        now_ms = time.monotonic() * 1000
                        for b in data:
                            c = chr(b).lower()
                            if c in ('w','a','s','d','m','q'):
                                pressed.add(c); last_seen[c] = now_ms
                                if c == 'm': auto = True
                                if c == 'q':
                                    self._apply_axes(0, 0)
                                    return
                    sweep()

                    if auto and any(k in pressed for k in ('w','a','s','d','q')):
                        auto = False

                    t = 1 if 'w' in pressed else (-1 if 's' in pressed else 0)
                    s = -1 if 'a' in pressed else (1 if 'd' in pressed else 0)
                    if 'w' in pressed and 's' in pressed: t = 0
                    if 'a' in pressed and 'd' in pressed: s = 0
                    if auto: t = 1

                    now = time.monotonic()
                    if (now - last_send) >= SEND:
                        last_send = now
                        self._apply_axes(s, t)
        finally:
            self._apply_axes(0, 0)
            print("[stdin] Listener exit.")

    # --- utilities ---
    def _apply_axes(self, s, t):
        self.steering = s
        self.throttle = t

    def _usable_showkey(self):
        return shutil.which("showkey") is not None

    def _on_real_vt(self):
        # best-effort: showkey needs a real console (not PTY)
        try:
            return os.isatty(sys.stdin.fileno())
        except Exception:
            return False








# ==============================
# Main
# ==============================
if __name__ == "__main__":
    print(f"WebSocket: ws://{WS_HOST}:{WS_CONTROL_PORT}")
    print(f"Streaming port: {STREAMING_PORT} | Process Video: {PROCESS_VIDEO}")

    client_socket = ClientSocket(server_ip=WS_HOST, server_port=WS_CONTROL_PORT)
    client = KeyboardController(client_socket)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        client_socket.close()  # fixed incomplete call
