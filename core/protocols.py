""" Created on Tue Nov 28 14:31:05 2023
    @author: dcupolillo """

import numpy as np
import time
import keyboard
import matplotlib.pyplot as plt
from serial import Serial
from dataclasses import dataclass, field
from typing import List

from pyhavior.core.serial_messages import (
    SerialMessages, SensorStateDecoder, KeyCommands)

__all__ = [
    "Habituation",
    "FearConditioning",
    "FearRecall",
    "TestRoaming"
]

# %% BehavioralTest


@dataclass
class BehavioralTest:

    """
    Base class to provide guidelines, common attributes, and methods
    for all behavioral test subclasses.

    Methods
    -------
    run:
        Run the behavioral test as a series of serial messages.
        Subclasses will provide specific implementations.
    display:
        Display the digital output waveform.
        Subclasses will provide specific implementations.

    Returns
    -------
    None

    """

    digital_outputs: List[str] = field(
         default_factory=lambda: ['Video', 'Tone', 'Shocker'])

    messages: 'SerialMessages' = field(
        default_factory=lambda: SerialMessages())

    keys: 'KeyCommands' = field(
        default_factory=lambda: KeyCommands())

    states: 'SensorStateDecoder' = field(
        default_factory=lambda: SensorStateDecoder())

    stop_requested: bool = field(default=False, init=False)

    running: bool = field(default=False, init=False)

    ser: 'Serial' = field(default=None, init=None)

    def __post_init__(self):
        "Any additional initialization logic for the base class"
        pass

    def run(self, ser: Serial, *args, **kwargs) -> None:
        """
        Generic method for starting serial communication.
        Contains the serial port initialization and the series of
        instructions (serial commands) to execute.

        Parameters
        ----------
        ser (Serial):
            The serial board object.
        *args
        **kwargs

        Returns
        -------
        None

        """

        self.ser = ser
        self.running = True

    def stop(self):

        if self.ser and self.ser.is_open:
            self.ser.close()
        self.running = False

    def request_stop(self):

        self.stop_requested = True

    def display(self, *args, **kwargs) -> None:
        """
        Generic display method to plot
        the states of digital outputs over time.

        Parameters
        ----------
        *args
        **kwargs

        Returns
        -------
        None

        """
        pass

# %% Habituation


@dataclass
class Habituation(BehavioralTest):

    def __post_init__(self) -> None:

        super().__post_init__()
        self.duration = 300

    def run(
            self,
            ser: Serial) -> None:

        self.ser = ser
        start_time = time.time()

        while (time.time() - start_time < self.duration and
               not self.stop_requested):
            pass


# %% FearConditioning


@dataclass
class FearConditioning(BehavioralTest):

    def __post_init__(
            self
    ) -> None:

        super().__post_init__()

        self.duration = 300
        self.buffer_time = 20

        self.tone_duration = 10
        self.intertone_interval = 60

        self.shock_duration = 1

        self.n_pairings = 5

        self.tone_onsets = (
            np.linspace(self.intertone_interval,
                        self.duration - self.intertone_interval,
                        self.n_pairings))

        self.tone_shock_delay = self.tone_duration - self.shock_duration
        self.shock_onsets = [tone_timestamp + self.tone_shock_delay
                             for tone_timestamp in self.tone_onsets]

        self.flag_timestamps = [False] * self.n_pairings

    def run(
            self,
            ser: Serial
    ) -> None:

        self.ser = ser

        self.timestamps = np.linspace(
            -self.buffer_time,
            self.duration + self.buffer_time,
            self.ser.baudrate)

        self.tone_states = [False] * len(self.timestamps)
        self.shock_states = [False] * len(self.timestamps)
        self.video_states = [False] * len(self.timestamps)

        start_time = time.time()

        while (time.time() - start_time < self.duration and
               not self.stop_requested):

            for i, t in enumerate(self.tone_onsets):

                if abs(time.time() - start_time - t) < 0.5:

                    if not self.flag_timestamps[i]:

                        self.flag_timestamps[i] = True
                        self.ser.write(self.messages.tone_on)
                        time.sleep(self.tone_shock_delay)

                        self.ser.write(self.messages.tone_on)
                        self.ser.write(self.messages.shock_on)
                        time.sleep(self.shock_duration)

                        self.ser.write(self.messages.tone_off)

                        # Shocker has a 2 sec hard-stop on Arduino
                        if self.shock_duration < 2:
                            self.ser.write(self.messages.shock_off)

        if self.ser:
            self.ser.close()

    def display(
            self
    ) -> None:

        for t, timestamp in enumerate(self.timestamps):

            for tone_onsets, shock_onsets in zip(
                    self.tone_onsets, self.shock_onsets):

                if 0 <= timestamp <= self.duration:
                    self.video_states[t] = True

                if (tone_onsets <= timestamp
                        <= tone_onsets + self.tone_duration):
                    self.tone_states[t] = True

                if (shock_onsets <= timestamp
                        <= shock_onsets + self.shock_duration):
                    self.shock_states[t] = True

        fig, ax = plt.subplots()

        states = {key: [] for key in self.digital_outputs}
        states = {'Video': self.video_states,
                  'Tone': self.tone_states,
                  'Shock': self.shock_states}

        y_ticks = [None] * ((len(self.digital_outputs)) * len(self.states))
        y_labels = [None] * ((len(self.digital_outputs)) * len(self.states))

        # Adjust the plotting of states and populate yTicks and yLabels
        offset = 1.5
        for i, (label, state) in enumerate(states.items()):
            plot_offset = offset * i
            ax.plot(self.timestamps,
                    [s + plot_offset for s in state],
                    label=label)

            (
                y_ticks[i * len(self.states) + False],
                y_ticks[i * len(self.states) + True]
            ) = plot_offset + 1, plot_offset

            (
                y_labels[i * len(self.states) + False],
                y_labels[i * len(self.states) + True]
            ) = self.states[1], self.states[0]

        ax.set_title(f"{type(self).__name__}")
        ax.set_xlabel("Time (s)")
        ax.set_yticks(y_ticks)
        ax.set_yticklabels(y_labels)
        ax.legend()

# %% FearRecall


@dataclass
class FearRecall(BehavioralTest):

    def __post_init__(
            self
    ) -> None:

        super().__post_init__()

        self.duration = 300
        self.tone_duration = 10
        self.shock_duration = 0
        self.intertone_interval = 60
        self.n_pairings = 5

        self.buffer_time = 20
        self.timestamps = np.linspace(
            -self.buffer_time,
            self.duration + self.buffer_time,
            1000)

        self.tone_onsets = (
            np.linspace(self.intertone_interval,
                        self.duration - self.intertone_interval,
                        self.n_pairings))
        self.shock_onsets = np.empty_like(self.tone_onsets)

        self.tone_states = [False] * len(self.timestamps)
        self.shock_states = [False] * len(self.timestamps)
        self.video_states = [False] * len(self.timestamps)

        self.flag_timestamps = [False] * self.n_pairings

    def run(
            self,
            ser: Serial
    ) -> None:

        self.ser = ser

        start_time = time.time()

        while (time.time() - start_time < self.duration and
               not self.stop_requested):

            for i, t in enumerate(self.tone_onsets):

                if abs(time.time() - start_time - t) < 0.5:

                    if not self.flag_timestamps[i]:

                        self.flag_timestamps[i] = True
                        self.ser.write(self.messages.tone_on)
                        time.sleep(self.tone_duration)
                        self.ser.write(self.messages.tone_off)

    def display(
            self
    ) -> None:

        for t, timestamp in enumerate(self.timestamps):

            for tone_onsets, shock_onsets in zip(
                    self.tone_onsets, self.shock_onsets):

                if 0 <= timestamp <= self.duration:
                    self.video_states[t] = True

                if (tone_onsets <= timestamp
                        <= tone_onsets + self.tone_duration):
                    self.tone_states[t] = True

                if (shock_onsets <= timestamp
                        <= shock_onsets + self.shock_duration):
                    self.shock_states[t] = True

        fig, ax = plt.subplots()

        states = {key: [] for key in self.digital_outputs}
        states = {'Video': self.video_states,
                  'Tone': self.tone_states,
                  'Shock': self.shock_states}

        y_ticks = [None] * ((len(self.digital_outputs)) * len(self.states))
        y_labels = [None] * ((len(self.digital_outputs)) * len(self.states))

        # Adjust the plotting of states and populate yTicks and yLabels
        offset = 1.5
        for i, (label, state) in enumerate(states.items()):
            plot_offset = offset * i
            ax.plot(self.timestamps,
                    [s + plot_offset for s in state],
                    label=label)

            (
                y_ticks[i * len(self.states) + False],
                y_ticks[i * len(self.states) + True]
            ) = plot_offset + 1, plot_offset
            (
                y_labels[i * len(self.states) + False],
                y_labels[i * len(self.states) + True]
            ) = self.states[1], self.states[0]

        ax.set_title(f"{type(self).__name__}")
        ax.set_xlabel("Time (s)")
        ax.set_yticks(y_ticks)
        ax.set_yticklabels(y_labels)
        ax.legend()


# %% FillTubes


@dataclass
class FillTubes(BehavioralTest):

    def __post_init__(
            self
    ) -> None:

        super().__post_init__()

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


# %% TestDigitalOutput


@dataclass
class TestDigitalOutput(BehavioralTest):

    def __post_init__(
            self
    ) -> None:

        super().__post_init__()

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


# %% TestAnalog

@dataclass
class TestAnalog(BehavioralTest):

    def __post_init__(
            self
    ) -> None:

        super().__post_init__()

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


# %%

@dataclass
class TestRoaming(BehavioralTest):

    def __post_init__(
            self
    ) -> None:

        super().__post_init__()

        self.sensor_states = {'Back Sensor': None,
                              'Side Sensor': None,
                              'Nose Sensor': None}
        self.state_changes = {'Back Sensor': [],
                              'Side Sensor': [],
                              'Nose Sensor': []}

        self.duration = 5

    def run(
            self,
            ser: Serial
    ) -> None:

        self.ser = ser

        start_time = time.time()

        while (time.time() - start_time < self.duration and
               not self.stop_requested):

            if self.ser.in_waiting > 0:

                current_time = time.time() - start_time

                data = ser.readline().decode().strip()
                interpreted_data = self.decoder.interpret(data)

                print(interpreted_data)

            else:
                break