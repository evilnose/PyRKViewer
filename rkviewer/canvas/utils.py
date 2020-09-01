"""Utility functions for the canvas.

This includes drawing helpers and 2D geometry functions.
"""
# pylint: disable=maybe-no-member
import wx
from typing import Any, Collection, List, Optional
from .geometry import Rect
from .data import Node


def super_hook(func):
    def ret(self, *args, **kw):
        super_method = getattr(super(self), func.__name__)
        super_method(*args, **kw)
        self.changed_fn()

    return ret


def get_nodes_by_idx(nodes: List[Node], indices: Collection[int]):
    """Simple helper that maps the given list of indices to their corresponding nodes."""
    ret = [n for n in nodes if n.index in indices]
    assert len(ret) == len(indices)
    return ret


def get_nodes_by_ident(nodes: List[Node], ids: Collection[str]):
    ret = [n for n in nodes if n.id_ in ids]
    assert len(ret) == len(ids)
    return ret



def draw_rect(gc: wx.GraphicsContext, rect: Rect, *, fill: Optional[wx.Colour] = None,
              border: Optional[wx.Colour] = None, border_width: float = 1,
              fill_style=wx.BRUSHSTYLE_SOLID, border_style=wx.PENSTYLE_SOLID):
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
        brush = wx.Brush(fill, fill_style)
        gc.SetBrush(brush)
    if border is not None:
        pen = gc.CreatePen(wx.GraphicsPenInfo(border).Width(border_width).Style(border_style))
        gc.SetPen(pen)

    # draw rect
    path = gc.CreatePath()
    path.AddRectangle(x, y, width, height)

    # finish drawing if applicable
    if fill is not None:
        gc.FillPath(path)
    if border is not None:
        gc.StrokePath(path)

