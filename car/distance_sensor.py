import board
import busio
import adafruit_vl53l0x
import threading
import time
from typing import Optional


class DistanceSensor:
    def __init__(self, address=0x29):
        self.i2c = busio.I2C(board.SCL_1, board.SDA_1)
        self.sensor = adafruit_vl53l0x.VL53L0X(self.i2c, address=address)
        self._last_distance: Optional[int] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
    def start(self):
        """Start continuous distance reading in background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        print("DistanceSensor started")
        
    def stop(self):
        """Stop the reading loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            
    def _read_loop(self):
        """Continuously read distance in background."""
        while self._running:
            try:
                distance = self.sensor.range
                with self._lock:
                    self._last_distance = distance
            except Exception as e:
                print(f"Distance sensor error: {e}")
            time.sleep(0.05)
            
    def get_distance(self) -> Optional[int]:
        """Get the last read distance in mm."""
        with self._lock:
            return self._last_distance


# For standalone testing
if __name__ == "__main__":
    sensor = DistanceSensor()
    sensor.start()
    print("VL53L0X ready! Reading distance...")
    
    try:
        while True:
            distance = sensor.get_distance()
            if distance is not None:
                print(f"{distance} mm")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        sensor.stop()

