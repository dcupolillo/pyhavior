"""
Pyhavior package initialization.

Pyhavior is a Python package to control a custom built conditioning cage
controlled by Arduino boards.
It allows to record videos of the animal behavior and to synchronize
the video with the Arduino serial commands.

Integrated with a simple GUI, it allows to run
behavioral protocols and save videos.
"""

__version__ = "0.1.0"

from gui.gui import run_app

import sys
from pathlib import Path


def _info():
    """display information about the pyhavior package."""
    import platform
    import numpy
    print("==== Pyhavior Information ====\n")
    print("Python", sys.version)
    print("System:", platform.system(), platform.release())
    print("numpy version:", numpy.__version__)
    print("Pyhavior version:", __version__)
    print("Pyhavior path:", Path(__file__).parent.resolve())
    print("\n")


def showInfo():
    _info()


def help():
    """launch the Pyhavior project page in a browser."""
    import webbrowser
    webbrowser.open(
        "http://github.com/dcupolillo/Pyhavior", new=2)


