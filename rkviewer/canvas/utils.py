"""Utility functions for the canvas.

This includes drawing helpers and 2D geometry functions.
"""
# pylint: disable=maybe-no-member
import wx
from typing import Optional
from .geometry import Rect


def super_hook(func):
    def ret(self, *args, **kw):
        super_method = getattr(super(self), func.__name__)
        super_method(*args, **kw)
        self.changed_fn()

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


class HookedSet(set):
    def __init__(self, *args, changed_fn, **kw):
        super().__init__(*args, **kw)
        self._changed_fn = changed_fn

    @classmethod
    def _wrap_methods(cls, names):
        def wrap_method_closure(name):
            def inner(self, *args):
                result = getattr(set, name)(self, *args)
                if isinstance(result, set) and not hasattr(result, '_changed_fn'):
                    result = cls(result, changed_fn=self._changed_fn)
                return result
            setattr(cls, name, inner)

        for name in names:
            wrap_method_closure(name)


HookedSet._wrap_methods(['__isub__', '__iand__', '__ixor__', '__ior__', 'add', 'remove', 'discard',
                         'pop', 'clear', 'difference_update', 'symmetric_difference_update',
                         'intersection_update', 'update'
                         ])
