""" 
Fill Tubes utility
Created on Tue Nov 28 14:31:05 2023
@author: dcupolillo 
"""

import time
import keyboard
from serial import Serial
from pyhavior.core.serial_messages import SerialMessages, KeyCommands


class FillTubes:
    """
    Fill Tubes utility
    
    Uses keyboard input to control a pump via serial communication.
    Useful for priming tubes.
    """

    def __init__(self) -> None:
        
        self.messages = SerialMessages()
        self.keys = KeyCommands()
        self.running = False
        self.ser = None

    def run(
            self,
            ser: Serial
    ) -> None:
        
        self.ser = ser
        self.running = True

        while self.running:

            if keyboard.is_pressed(self.keys.pump_on):
                self.ser.write(self.messages.pump_on)
                time.sleep(0.01)
                self.ser.write(self.messages.pump_off)

            time.sleep(0.01)  # Sleep to reduce CPU usage

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