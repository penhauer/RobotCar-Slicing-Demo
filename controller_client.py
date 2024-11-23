import traitlets
import socket
import threading
import json
import keyboard  # Library to handle keyboard inputs
import time


class ControllerClient(traitlets.HasTraits):
    steering = traitlets.Int()  # Trait for steering
    throttle = traitlets.Int()  # Trait for throttle
    change = traitlets.Dict()   # Combined change dictionary
    
    @traitlets.validate('change')
    def _clip_change(self, proposal):
        return proposal['value']
    
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.connect()
        self.setup_trait_links()
        
        # Start the keyboard listener in a separate thread
        self.keyboard_thread = threading.Thread(target=self.keyboard_listener)
        self.keyboard_thread.start()

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.server_ip, self.server_port))
        
    def setup_trait_links(self):
        """Link steering and throttle to update the change dictionary."""
        traitlets.dlink((self, 'steering'), (self, 'change'), transform=self._update_steering)
        traitlets.dlink((self, 'throttle'), (self, 'change'), transform=self._update_throttle)
    
    def _update_steering(self, value):
        """Update the steering in the change dictionary."""
        current_change = self.change.copy()
        current_change['steering'] = value
        current_change['type'] = 'steering'
        return current_change

    def _update_throttle(self, value):
        """Update the throttle in the change dictionary."""
        current_change = self.change.copy()
        current_change['throttle'] = value
        current_change['type'] = 'throttle'
        return current_change
    
    def keyboard_listener(self):
        """Listen for keyboard inputs and update traits."""
        print("Listening for keyboard inputs. Use W/A/S/D for control. Press Q to quit.")
        
        try:
            while True:
                new_steering = 0  # Reset steering
                new_throttle = 0  # Reset throttle
                
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
                
                # Update the throttle and steering traits
                self.steering = new_steering
                self.throttle = new_throttle
                
                # Quit condition
                if keyboard.is_pressed('q'):
                    print("Exiting keyboard listener...")
                    break

                # Add a short delay to prevent high CPU usage
                time.sleep(0.1)

        except KeyboardInterrupt:
            print("Keyboard listener interrupted.")
        finally:
            print("Keyboard listener shutting down...")

    @traitlets.observe('change')
    def _on_change(self, d):
        """Send the changed value to the server."""
        print(f"Sending message to server: {d}")
        msg = self.change
        msg = {
            'new': d['new'],
        }
        try:
            self.sock.sendall(json.dumps(msg).encode('ascii'))
        except Exception as e:
            print("Send failed with error. Restarting the socket.")
            print(e)
            self.reset_connection()
        
    def reset_connection(self):
        self.close()
        self.connect()
    
    def close(self):
        self.sock.close()


# Example usage
client = ControllerClient(server_ip='localhost', server_port=9999)

