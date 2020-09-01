# pylint: disable=maybe-no-member
import wx
from dataclasses import dataclass

@dataclass
class CanvasState:
    """The current global state of the canvas.

    Attributes:
        scale: The zoom scale of the canvas.
        multi_select: Whether the user is pressing the keys that signify multiple selection of
                      items.
    """
    scale: float = 1
    
    @property
    def multi_select(self):
        return wx.GetKeyState(wx.WXK_CONTROL) or wx.GetKeyState(wx.WXK_SHIFT)

cstate = CanvasState()
