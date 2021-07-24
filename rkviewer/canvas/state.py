# pylint: disable=maybe-no-member
import wx
from rkviewer.config import DEFAULT_ARROW_TIP
from rkviewer.canvas.geometry import Rect, Vec2
import copy
from dataclasses import dataclass
from enum import Enum, unique
from typing import Any, Callable, List, Tuple

@unique
class InputMode(Enum):
    """Enum for the current input mode of the canvas."""
    SELECT = 'Select'
    ADD_NODES = 'Add Nodes'
    ADD_COMPARTMENTS = 'Add Compartments'
    ZOOM = 'Zoom'

    def __str__(self):
        return str(self.value)


class ArrowTip:
    points: List[Vec2]

    def __init__(self, points: List[Vec2]):
        if len(points) != 4:
            raise ValueError('Arrow tip must consist of 4 points!')
        self.points = points

    def clone(self):
        return ArrowTip(copy.copy(self.points))


@dataclass
class CanvasState:
    """The current global state of the canvas.

    Attributes:
        scale: The zoom scale of the canvas.
        multi_select: Whether the user is pressing the keys that signify multiple selection of
                      items.
    """
    scale: float = 1
    bounds: Rect = Rect(Vec2(), Vec2())
    input_mode_changed: Callable[[InputMode], None] = lambda _: None
    _input_mode: InputMode = InputMode.SELECT
    arrow_tip: ArrowTip = ArrowTip(copy.copy(DEFAULT_ARROW_TIP))

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
