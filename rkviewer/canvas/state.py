# pylint: disable=maybe-no-member
import wx
from dataclasses import dataclass
from enum import Enum, unique
from typing import Any, Callable


@unique
class InputMode(Enum):
    """Enum for the current input mode of the canvas."""
    SELECT = 'Select'
    ADD = 'Add'
    ZOOM = 'Zoom'

    def __str__(self):
        return str(self.value)


@dataclass
class CanvasState:
    """The current global state of the canvas.

    Attributes:
        scale: The zoom scale of the canvas.
        multi_select: Whether the user is pressing the keys that signify multiple selection of
                      items.
    """
    scale: float = 1
    input_mode_changed: Callable[[InputMode], None] = lambda _: None
    _input_mode: InputMode = InputMode.SELECT

    @property
    def input_mode(self):
        return self._input_mode

    @input_mode.setter
    def input_mode(self, mode: InputMode):
        self._input_mode = mode
        self.input_mode_changed(mode)
    
    @property
    def multi_select(self):
        return wx.GetKeyState(wx.WXK_CONTROL) or wx.GetKeyState(wx.WXK_SHIFT)

cstate = CanvasState()
