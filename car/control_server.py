import subprocess
import threading
from twisted.internet import reactor, protocol
import time
import json
import threading
import sys

car = None

class ControllerServerProtocol(protocol.Protocol):
    def dataReceived(self, data):
        message = data.decode('utf-8')
        print(f"Received from client: {message}")
        if car == None:
            print("Warning: messaged received but car is not set")
        else:
            try:
                commands = message.strip().split("\n")
                for command in commands:
                    d = json.loads(command)
                    print("decoded command: ", d)
                    control_the_car(d)
            except Exception as e:
                print("Error in decoding control payload. payload:")
                print(f"|{message}|")
                for command in commands:
                    print(f"/{command}/")
                print("error:")
                print(e)


def control_the_car(d: dict):
    t = d["new"]["type"]
    if t == "steering":
        car._on_steering(d["new"])
    elif t == "throttle":
        car._on_throttle(d["new"])
    else:
        raise Exception(f"Unknown command type '{t}'")


class ControllerServerFactory(protocol.Factory):
    def buildProtocol(self, addr):
        print(f"Connection from {addr}")
        return ControllerServerProtocol()

def monitor_ssh_tunnel(ssh_process):
    """
    Monitors the SSH process for output and errors and prints them to the console.
    """
    while True:
        # Read output and error streams
        output = ssh_process.stdout.readline()
        error = ssh_process.stderr.readline()
        
        # Print any output or error
        if output:
            print(f"SSH Output: {output.decode().strip()}")
        if error:
            print(f"SSH Error: {error.decode().strip()}")
        
        # Check if process is still running
        if ssh_process.poll() is not None:  # Process has terminated
            print("SSH tunnel process has terminated.")
            break
        time.sleep(1)


def find_pid_of_reverse_tunnel(remote_host, remote_port, remote_password):
    remote_command = (
        f"echo '{remote_password}'"
        f"| sudo -S lsof 2>/dev/null -i :{remote_port}"
        " | grep -E 'sshd.*IPv4.*LISTEN'"
    )

    ssh_command = f"ssh {remote_host} \"{remote_command}\" " + " | awk ' {print $2} ' "

    result = subprocess.run(
        ssh_command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    pid = result.stdout.strip()
    return pid


def kill_pid(remote_host, remote_port, pid):
    print(f"killing process {pid} on remote")
    ssh_command = [
        "ssh",
        f"{remote_host}",
        f"kill -9 {pid}"
    ]

    subprocess.run(ssh_command) 


def kill_the_old_tunnel(remote_host, remote_port, remote_password):
    pid = find_pid_of_reverse_tunnel(remote_host, remote_port, remote_password)
    if pid:
        kill_pid(remote_host, remote_port, pid)


def start_reverse_ssh_tunnel(remote_host, remote_port, remote_password, local_port):
    kill_the_old_tunnel(remote_host, remote_port, remote_password)
    ssh_command = [
        "ssh",
        "-N",
        "-R", f"localhost:{remote_port}:localhost:{local_port}",
        f"{remote_host}",
    ]

    try:
        print(f"Establishing SSH tunnel to {remote_host} -> localhost:{local_port}")
        ssh_process = subprocess.Popen(
            ssh_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            # text=True
        )
        

        # monitor_thread = threading.Thread(target=monitor_ssh_tunnel, args=(ssh_process,))
        # monitor_thread.daemon = True
        # monitor_thread.start()
        
        # Wait a moment to ensure the tunnel is established
        time.sleep(2)
        
        if ssh_process.poll() is None:  # Process is running
            print("SSH tunnel established successfully.")
            return ssh_process
        else:
            print("Failed to establish SSH tunnel.")
            return None
    except Exception as e:
        print(f"Error starting SSH tunnel: {e}")
        return None

def start_twisted_server(port):
    reactor.listenTCP(port, ControllerServerFactory())
    print(f"Twisted server listening on localhost:{port}...")
    reactor.run()


def start_the_car():
    print("starting the car...")
    from jetracer.nvidia_racecar import NvidiaRacecar
    global car
    car = NvidiaRacecar()
    car.throttle_gain = 0.2
    car.steering_offset=0.3
    car.steering = 0
    print("Car object successfully created")

def main():
    remote_host = sys.argv[1]
    remote_port = int(sys.argv[2])
    remote_password = sys.argv[3]
    print("serving on port", remote_port, "and reverse ssh: ", remote_host, remote_port)
    local_port = remote_port

    
    ssh_tunnel = start_reverse_ssh_tunnel(remote_host, remote_port, remote_password, local_port)

    if ssh_tunnel:
        try:
            threading.Thread(target=start_the_car).start()
            start_twisted_server(local_port)
        finally:
            ssh_tunnel.terminate()
            print("SSH tunnel closed.")
    else:
        print("Failed to establish the SSH tunnel. Twisted server not started.")

main()

