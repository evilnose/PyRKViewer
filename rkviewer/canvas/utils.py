"""Utility functions for the canvas.

This includes drawing helpers and 2D geometry functions.
"""
# pylint: disable=maybe-no-member
import wx
import abc
from typing import Collection, Generic, List, Optional, Set, TypeVar, Callable
from .geometry import Rect
from .data import Node


def get_nodes_by_idx(nodes: List[Node], indices: Collection[int]):
    """Simple helper that maps the given list of indices to their corresponding nodes."""
    ret = [n for n in nodes if n.index in indices]
    assert len(ret) == len(indices)
    return ret


def get_nodes_by_ident(nodes: List[Node], ids: Collection[str]):
    """Simple helper that maps the given list of IDs to their corresponding nodes."""
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
    assert not(fill is None and border is None), \
        "Both 'fill' and 'border' are None, but at least one of them should be provided"

    assert not (border is not None and border_width == 0), \
        "'border_width' cannot be 0 when 'border' is specified"

    x, y = rect.position
    width, height = rect.size

    pen: wx.Pen
    brush: wx.Brush
    # set up brush and pen if applicable
    if fill is not None:
        brush = gc.CreateBrush(wx.Brush(fill, fill_style))
    else:
        brush = wx.TRANSPARENT_BRUSH
    if border is not None:
        pen = gc.CreatePen(wx.GraphicsPenInfo(border).Width(border_width).Style(border_style))
    else:
        pen = wx.TRANSPARENT_PEN

    gc.SetPen(pen)
    gc.SetBrush(brush)

    # draw rect
    gc.DrawRectangle(x, y, width, height)


"""Classes for the observer-Subject interface. See https://en.wikipedia.org/wiki/Observer_pattern
"""
T = TypeVar('T')


class Observer(abc.ABC, Generic[T]):
    """Observer abstract base class; encapsulates object of type T."""

    def __init__(self, update_callback: Callable[[T], None]):
        self.update = update_callback


class Subject(Generic[T]):
    """Subject abstract base class; encapsulates object of type T."""
    _observers: List[Observer]
    _item: T

    def __init__(self, item):
        self._observers = list()
        self._item = item

    def attach(self, observer: Observer):
        """Attach an observer."""
        self._observers.append(observer)

    def detach(self, observer: Observer):
        """Detach an observer."""
        self._observers.remove(observer)

    def notify(self) -> None:
        """Trigger an update in each Subject."""

        for observer in self._observers:
            observer.update(self._item)


class SetSubject(Subject[Set[T]]):
    """Subject class that encapsulates a set."""

    def __init__(self, *args):
        super().__init__(set(*args))

    def item_copy(self) -> Set:
        """Return a copy of the encapsulated set."""
        return set(self._item)

    def set_item(self, item: Set):
        """Update the value of the item, notifying observers if the new value differs from the old.
        """
        equal = self._item == item
        self._item = item
        if not equal:
            self.notify()

    def remove(self, el: T):
        """Remove an element from the set, notifying observers if the set changed."""
        equal = el not in self._item
        self._item.remove(el)
        if not equal:
            self.notify()

    def add(self, el: T):
        """Add an element from the set, notifying observers if the set changed."""
        equal = el in self._item
        self._item.add(el)
        if not equal:
            self.notify()
