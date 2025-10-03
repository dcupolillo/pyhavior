""" 
Test Analog utility
Created on Tue Nov 28 14:31:05 2023
@author: dcupolillo 
"""

import time
from serial import Serial
from pyhavior.core.serial_messages import SensorStateDecoder


class TestAnalog:
    """
    Test Analog utility

    Uses serial communication to read and interpret analog sensor data.
    """

    def __init__(self) -> None:
        
        self.states = SensorStateDecoder()
        self.running = False
        self.ser = None

    def run(
            self,
            ser: Serial
    ) -> None:
        
        self.ser = ser
        self.running = True

        while self.running:

            if self.ser and self.ser.is_open and self.ser.in_waiting > 0:
                data = self.ser.readline().decode().strip()
                interpreted_data = self.states.interpret(data)
                print(interpreted_data)

            time.sleep(0.1)

        if self.ser and getattr(self.ser, 'is_open', False):
            try:
                self.ser.close()
            except Exception:
                pass
    
    def stop(self) -> None:
        """Stop the test"""
        self.running = False
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass

    def request_stop(self) -> None:
        """Request test to stop"""
        self.running = False