"""Utility functions for the canvas.

This includes drawing helpers and 2D geometry functions.
"""
# pylint: disable=maybe-no-member
import wx
from typing import Optional, List
from ..utils import Vec2, Rect


def within_rect(pos: Vec2, rect: Rect) -> bool:
    """Returns whether the given position is within the rectangle, inclusive.
    """
    end = rect.position + rect.size
    return pos.x >= rect.position.x and pos.y >= rect.position.y and pos.x <= end.x and \
        pos.y <= end.y


def draw_rect(gc: wx.GraphicsContext, rect: Rect, *, fill: Optional[wx.Colour] = None,
             border: Optional[wx.Colour] = None, border_width: float = 1):
    """Draw a rectangle with the given graphics context.

    Either fill or border must be specified to avoid drawing an entirely transparent rectangle.
    
    Args:
        gc: The graphics context.
        rect: The rectangle to draw.
        fill: If specified, the fill color of the rectangle.
        border: If specified, the border color of the rectangle.
        border_width: The width of the borders. Defaults to 1. This cannot be 0 when border
            is specified.
    """
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


def get_bounding_rect(rects: List[Rect], padding: float = 0) -> Rect:
    """Compute the bounding rectangle of a given list of rects.

    This computes the smallest possible rectangle needed to cover each of the rects (inclusive), as
    well as its position. Additionally a padding may be specified to provide some space.

    Args:
        rets: The list of rectangles.
        padding: The padding of the bounding rectangle. If positive, there will be x pixels of 
            padding for each side of the rectangle.

    Returns:
        The bounding rectangle.
    """
    min_x = min(r.position.x for r in rects)
    min_y = min(r.position.y for r in rects)
    max_x = max(r.position.x + r.size.x for r in rects)
    max_y = max(r.position.y + r.size.y for r in rects)
    size_x = max_x - min_x + padding * 2
    size_y = max_y - min_y + padding * 2
    return Rect(Vec2(min_x - padding, min_y - padding), Vec2(size_x, size_y))


def clamp_rect_pos(rect: Rect, bounds: Rect, padding = 0) -> Vec2:
    """Clamp the position of rect, so that it is entirely within the bounds rectangle.

    The position is clamped such that the new position of the rectangle moves the least amount
    of distance possible.

    Note:
        The clamped rectangle must be able to fit inside the bounds rectangle, inclusive. The
        given rect is not modified, but a position is returned.

    Returns:
        The clamped position.
    """

    if rect.size.x + 2 * padding > bounds.size.x or rect.size.y + 2 * padding > bounds.size.y:
        raise ValueError("The clamped rectangle cannot fit inside the given bounds")

    topleft = bounds.position + Vec2.repeat(padding)
    botright = bounds.position + bounds.size - rect.size - Vec2.repeat(padding)
    ret = rect.position
    ret = Vec2(max(ret.x, topleft.x), ret.y)
    ret = Vec2(min(ret.x, botright.x), ret.y)
    ret = Vec2(ret.x, max(ret.y, topleft.y))
    ret = Vec2(ret.x, min(ret.y, botright.y))
    return ret


def clamp_point(pos: Vec2, bounds: Rect, padding = 0) -> Vec2:
    """Clamp the given point (pos) so that it is entirely within the bounds rectangle. 

    This is the same as calling clamp_rect_pos() with a clamped rectangle of size 1x1.

    Returns:
        The clamp position.
    """
    topleft = bounds.position + Vec2.repeat(padding)
    botright = bounds.position + bounds.size - Vec2.repeat(padding)
    ret = pos
    ret = Vec2(max(ret.x, topleft.x), ret.y)
    ret = Vec2(min(ret.x, botright.x), ret.y)
    ret = Vec2(ret.x, max(ret.y, topleft.y))
    ret = Vec2(ret.x, min(ret.y, botright.y))
    return ret


def rects_overlap(r1: Rect, r2: Rect) -> bool:
    """Returns whether the two given rectangles overlap, counting if they are touching."""
    botright1 = r1.position + r1.size
    botright2 = r2.position + r2.size

    # The two rects do not overlap if and only if the two rects do not overlap along at least one
    # of the axes.
    for axis in [0, 1]:
        if botright1[axis] < r2.position[axis] or botright2[axis] < r1.position[axis]:
            return False

    return True
