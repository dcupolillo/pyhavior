"""
GUI frames package for pyhavior.

Contains frame classes for organizing GUI layout.
"""

from .info_display import InfoDisplayFrame
from .settings import SettingsFrame
from .save import SaveFrame
from .record import RecordFrame

__all__ = ['InfoDisplayFrame', 'SettingsFrame', 'SaveFrame', 'RecordFrame']