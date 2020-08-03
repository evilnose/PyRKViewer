"""List of utility functions
"""
# pylint: disable=maybe-no-member
import wx
from .types import Rect, Vec2


def IodToWxColour(rgb: int, alpha: float):
    b = rgb & 0xff
    g = (rgb >> 8) & 0xff
    r = (rgb >> 16) & 0xff
    return wx.Colour(r, g, b, int(alpha * 255))


def WithinRect(pos: Vec2, rect: Rect) -> bool:
    end = rect.position + rect.size
    return pos.x >= rect.position.x and pos.y >= rect.position.y and pos.x <= end.x and \
        pos.y <= end.y


def DrawRect(gc: wx.GraphicsContext, rect: Rect, fill: wx.Colour, *,
                    border: wx.Colour = None, border_width: float = 0):
    """Draw a rectangle on the given graphics context."""
    if border is None:
        border = fill

    x, y = rect.position
    width, height = rect.size

    brush = wx.Brush(fill, wx.BRUSHSTYLE_SOLID)
    gc.SetBrush(brush)
    pen = gc.CreatePen(wx.GraphicsPenInfo(border).Width(border_width))
    gc.SetPen(pen)
    path = gc.CreatePath()
    path.AddRectangle(x, y, width, height)

    gc.FillPath(path)
    if border_width != 0:
        gc.StrokePath(path)