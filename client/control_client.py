import subprocess
import traitlets
import socket
import threading
import json
import keyboard
import time
import argparse

from video_processing import capture_thread, command_dict


class ClientSocket():
    
    def __init__(self, server_ip, server_port) -> None:
        self.server_ip = server_ip
        self.server_port = server_port
        self.connect()

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.server_ip, self.server_port))

    def send(self, msg):
        self.sock.sendall(json.dumps(msg).encode('ascii'))

    def reset_connection(self):
        self.close()
        self.connect()
    
    def close(self):
        self.sock.close()


class KeyboardController(traitlets.HasTraits):
    steering = traitlets.Int()  # Trait for steering
    throttle = traitlets.Int()  # Trait for throttle
    change = traitlets.Dict()   # Combined change dictionary
    
    @traitlets.validate('change')
    def _clip_change(self, proposal):
        return proposal['value']
    
    def __init__(self, client_socket: ClientSocket, args):
        self.client_socket = client_socket
        self.setup_trait_links()

        if args.process_video:
            self.camera_thread = threading.Thread(target=capture_thread, args=(args.port, ))
            self.camera_thread.start()
        else:
            print("Opening the camera display process")
            subprocess.Popen(["./show_video.sh", str(args.port)])
        
        self.keyboard_thread = threading.Thread(target=self.keyboard_listener)
        self.keyboard_thread.start()

    def setup_trait_links(self):
        traitlets.dlink((self, 'steering'), (self, 'change'), transform=self._update_steering)
        traitlets.dlink((self, 'throttle'), (self, 'change'), transform=self._update_throttle)
    
    def _update_steering(self, value):
        current_change = self.change.copy()
        current_change['steering'] = value
        current_change['type'] = 'steering'
        return current_change

    def _update_throttle(self, value):
        current_change = self.change.copy()
        current_change['throttle'] = value
        current_change['type'] = 'throttle'
        return current_change
    
    def keyboard_listener(self):
        print(
            """
                Listening for keyboard inputs.
                Use W/A/S/D for control.
                Press M for automatic move
                Press Q to quit.
            """
        )
        
        running = True
        new_steering = 0
        new_throttle = 0
        try:
            while running:
                if command_dict["move"]:
                    if len(keyboard._pressed_events) > 0:
                        command_dict["move"] = False

                    if command_dict["obstacle"]:
                        new_throttle = 0
                        command_dict["move"] = False
                
                if not command_dict["move"]:
                    if keyboard.is_pressed('w'):  # Forward
                        new_throttle = 1
                    elif keyboard.is_pressed('s'):  # Backward
                        new_throttle = -1
                    else:
                        new_throttle = 0

                    if keyboard.is_pressed('a'):  # Left
                        new_steering = -1
                    elif keyboard.is_pressed('d'):  # Right
                        new_steering = 1
                    else:
                        new_steering = 0

                    if keyboard.is_pressed('m'):
                        command_dict["move"] = True
                        new_throttle = 1

                if keyboard.is_pressed('q'):
                    new_throttle = 0
                    new_steering = 0
                    running = False
                    print("Exiting keyboard listener...")
                
                self.steering = new_steering
                self.throttle = new_throttle
                
                time.sleep(0.05)

        except KeyboardInterrupt:
            print("Keyboard listener interrupted.")
        finally:
            print("Keyboard listener shutting down...")

    @traitlets.observe('change')
    def _on_change(self, d):
        print(f"Sending message to server: {d}")
        msg = self.change
        msg = {
            'new': d['new'],
        }
        try:
            self.client_socket.send(msg)
        except Exception as e:
            print("Send failed with error. Restarting the socket.")
            print(e)
            self.client_socket.reset_connection()


def parse_args():
    parser = argparse.ArgumentParser(description="Process command-line arguments")

    parser.add_argument(
        "port", 
        type=int, 
        help="The port number (mandatory argument)"
    )
    parser.add_argument(
        "--process_video", 
        action="store_true", 
        help="Flag to indicate whether to process video (optional)"
    )

    args = parser.parse_args()
    print(f"Port: {args.port}")
    print(f"Process Video: {args.process_video}")
    return args

if __name__ == "__main__":
    args = parse_args()

    client_socket = ClientSocket(server_ip='localhost', server_port=9999)
    client = KeyboardController(client_socket, args)

