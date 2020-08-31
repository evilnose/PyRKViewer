# pylint: disable=maybe-no-member
import wx
from dataclasses import dataclass

@dataclass
class CanvasState:
    scale: float = 1
    
    @property
    def multi_select(self):
        return wx.GetKeyState(wx.WXK_CONTROL) or wx.GetKeyState(wx.WXK_SHIFT)

cstate = CanvasState()
