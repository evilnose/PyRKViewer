"""List of utility functions
"""
# pylint: disable=maybe-no-member
import wx
from typing import List, Optional
from .types import Node, Rect, Vec2


def IodToWxColour(rgb: int, alpha: float):
    b = rgb & 0xff
    g = (rgb >> 8) & 0xff
    r = (rgb >> 16) & 0xff
    return wx.Colour(r, g, b, int(alpha * 255))


def WithinRect(pos: Vec2, rect: Rect) -> bool:
    end = rect.position + rect.size
    return pos.x >= rect.position.x and pos.y >= rect.position.y and pos.x <= end.x and \
        pos.y <= end.y


def DrawRect(gc: wx.GraphicsContext, rect: Rect, *, fill: Optional[wx.Colour] = None,
             border: Optional[wx.Colour] = None, border_width: float = 1):
    """Draw a rectangle on the given graphics context."""
    if fill is None and border is None:
        raise ValueError("Both 'fill' and 'border' are None, but at least one of them should be "
                         "provided")

    if border is not None and border_width == 0:
        raise ValueError("'border_width' cannot be 0 when 'border' is specified")

    x, y = rect.position
    width, height = rect.size

    # set up brush and pen if applicable
    if fill is not None:
        brush = wx.Brush(fill, wx.BRUSHSTYLE_SOLID)
        gc.SetBrush(brush)
    if border is not None:
        pen = gc.CreatePen(wx.GraphicsPenInfo(border).Width(border_width))
        gc.SetPen(pen)

    # draw rect
    path = gc.CreatePath()
    path.AddRectangle(x, y, width, height)

    # finish drawing if applicable
    if fill is not None:
        gc.FillPath(path)
    if border is not None:
        gc.StrokePath(path)


def GetBoundingRect(nodes: List[Node], padding: float = 0) -> Rect:
    min_x = min(n.s_position.x for n in nodes)
    min_y = min(n.s_position.y for n in nodes)
    max_x = max(n.s_position.x + n.s_size.x for n in nodes)
    max_y = max(n.s_position.y + n.s_size.y for n in nodes)
    size_x = max_x - min_x + padding * 2
    size_y = max_y - min_y + padding * 2
    return Rect(Vec2(min_x - padding, min_y - padding), Vec2(size_x, size_y))


def ClampRectPos(rect: Rect, bounds: Rect, padding = 0) -> Vec2:
    topleft = bounds.position + Vec2.repeat(padding)
    botright = bounds.size - rect.size - Vec2.repeat(padding)
    ret = rect.position
    ret = Vec2(max(ret.x, topleft.x), ret.y)
    ret = Vec2(min(ret.x, botright.x), ret.y)
    ret = Vec2(ret.x, max(ret.y, topleft.y))
    ret = Vec2(ret.x, min(ret.y, botright.y))
    return ret


def ClampPoint(pos: Vec2, bounds: Rect, padding = 0) -> Vec2:
    topleft = bounds.position + Vec2.repeat(padding)
    botright = bounds.size - Vec2.repeat(padding)
    ret = pos
    ret = Vec2(max(ret.x, topleft.x), ret.y)
    ret = Vec2(min(ret.x, botright.x), ret.y)
    ret = Vec2(ret.x, max(ret.y, topleft.y))
    ret = Vec2(ret.x, min(ret.y, botright.y))
    return ret
