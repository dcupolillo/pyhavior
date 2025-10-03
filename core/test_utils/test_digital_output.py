""" 
Test Digital Output utility
Created on Tue Nov 28 14:31:05 2023
@author: dcupolillo 
"""

import keyboard
from serial import Serial
from pyhavior.core.serial_messages import SerialMessages, KeyCommands


class TestDigitalOutput:
    """
    Test Digital Output utility
     
    Uses keyboard inputs to control digital outputs via serial communication.
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

            if keyboard.is_pressed(self.keys.tone_on):
                self.ser.write(self.messages.tone_on)

            if keyboard.is_pressed(self.keys.tone_off):
                self.ser.write(self.messages.tone_off)

            if keyboard.is_pressed(self.keys.buzzer_on):
                self.ser.write(self.messages.buzzer_on)

            if keyboard.is_pressed(self.keys.buzzer_off):
                self.ser.write(self.messages.buzzer_off)

            if keyboard.is_pressed(self.keys.whitenoise_on):
                self.ser.write(self.messages.white_noise_on)

            if keyboard.is_pressed(self.keys.whitenoise_off):
                self.ser.write(self.messages.white_noise_off)

            if keyboard.is_pressed(self.keys.pump_on):
                self.ser.write(self.messages.pump_on)

            if keyboard.is_pressed(self.keys.pump_off):
                self.ser.write(self.messages.pump_off)

            if keyboard.is_pressed(self.keys.shock_on):
                self.ser.write(self.messages.shock_on)

            if keyboard.is_pressed(self.keys.shock_off):
                self.ser.write(self.messages.shock_off)
        
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