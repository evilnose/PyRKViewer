"""Utility functions"""
from __future__ import annotations  # For returning self in a class
# pylint: disable=maybe-no-member
import wx
import copy
import os
import sys
from typing import Any, Callable, Collection, List, Tuple, TypeVar


TNum = TypeVar('TNum', float, int)  #: A custom number type, either float or int.


class Vec2:
    """Class that represents a 2D vector. Supports common vector operations like add and sub.
    
    Note:
        Vec2 objects are immutable, meaning one cannot modify elements of the vector.
    """
    x: TNum
    y: TNum
    _i: int

    def __init__(self, x=None, y=None):
        """Initialize a 2D vector.

        If two arguments are specified, they are considered the x and y coordinate
        of the Vec2.

        If only one argument is specified, it should be an iterable of two elements,
        which will be unwrapped as x and y.
        """
        self._i = 0
        if x is None:
            if y is not None:
                raise ValueError('x cannot be None when y is not None. Use one of three '
                                 'constructors: Vec2(x, y), Vec2(Other(x, y)), or Vec2()')
            else:
                self.x = 0
                self.y = 0

        elif y is None:
            self.x, self.y = x
        else:
            self.x = x
            self.y = y

    def __iter__(self) -> Vec2:
        self._i = 0
        return self

    def __next__(self) -> TNum:
        if self._i == 0:
            self._i += 1
            return self.x
        elif self._i == 1:
            self._i += 1
            return self.y
        else:
            raise StopIteration

    def __add__(self, other) -> Vec2:
        return Vec2(self.x + other.x, self.y + other.y)

    __iadd__ = __add__

    def __sub__(self, other) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    __isub__ = __sub__

    def __mul__(self, k) -> Vec2:
        return Vec2(self.x * k, self.y * k)

    __rmul__ = __mul__

    __imul__ = __mul__

    def __truediv__(self, k) -> Vec2:
        return Vec2(self.x / k, self.y / k)

    def __repr__(self) -> str:
        return '({}, {})'.format(self.x, self.y)

    def __getitem__(self, i: int):
        if i == 0:
            return self.x
        elif i == 1:
            return self.y
        else:
            raise IndexError("Tried to get axis {} of a Vec2".format(i))

    def swapped(self, i: int, val: TNum):
        """Return a Vec2 equal to this one but with the ith element swapped for val."""
        if i == 0:
            return Vec2(val, self.y)
        elif i == 1:
            return Vec2(self.x, val)
        else:
            raise IndexError("Tried to swap axis {} of a Vec2".format(i))

    def __len__(self) -> int:
        return 2

    def __eq__(self, other: Vec2) -> bool:
        return self.x == other.x and self.y == other.y

    def to_wx_point(self) -> wx.Point:
        """Convert this to wx.Point; return the result."""
        return wx.Point(self.x, self.y)

    # element-wise multiplication
    def elem_mul(self, other: Vec2) -> Vec2:
        """Return the resulting Vec2 by performing element-wise multiplication.
        
        Examples:
            >>> c = a.elem_mul(b)  # is equivalent to...
            >>> c = Vec2(a.x * b.x, a.y * b.y)
        """
        return Vec2(self.x * other.x, self.y * other.y)

    def elem_div(self, other: Vec2) -> Vec2:
        """Return the resulting Vec2 by performing element-wise division.
        
        Examples:
            >>> c = a.elem_div(b)  # is equivalent to...
            >>> c = Vec2(a.x / b.x, a.y / b.y)
        """
        return Vec2(self.x / other.x, self.y / other.y)

    def elem_abs(self) -> Vec2:
        """Return the Vec2 obtained by taking the element-wise absolute value of this Vec2."""
        return Vec2(abs(self.x), abs(self.y))

    def map(self, op: Callable[[TNum], Any]) -> Vec2:
        """Map the given operation across the two elements of the vector."""
        return Vec2(op(self.x), op(self.y))

    @classmethod
    def repeat(cls, val: TNum = 1) -> Vec2:
        """Return the Vec2 obtained by repeating the given scalar value across the two elements.
        
        Examples:

            >>> print(Vec2.repeat(5.4))
            (5.4, 5.4)
        """
        return Vec2(val, val)


class Rect:
    """Class that represents a rectangle by keeping a position and a size."""
    def __init__(self, pos: Vec2, size: Vec2):
        assert size.x >= 0 and size.y >= 0
        self.position = pos
        self.size = size

    def __eq__(self, other: Rect) -> bool:
        return self.position == other.position and self.size == other.size

    def as_tuple(self) -> Tuple[Vec2, Vec2]:
        """Return the position and the size in a tuple."""
        return (self.position, self.size)

    def nth_vertex(self, n: int):
        """Return the nth vertex of the rectangle.
        
        The top-left vertex is the 0th vertex, and subsequence vertices are indexed in clockwise
        fashion.
        """
        if n == 0:
            return self.position
        elif n == 1:
            return self.position + Vec2(self.size.x, 0)
        elif n == 2:
            return self.position + self.size
        elif n == 3:
            return self.position + Vec2(0, self.size.y)
        else:
            assert False, "Rect.nth_vertex() index out of bounds"

    def __repr__(self):
        return 'Rect({}, {})'.format(self.position, self.size)


class Node:
    """Class that represents a Node for rendering purposes.
    
    Attributes:
        index: The index of the node. If this node has not yet been added to the NOM, this takes on
               the value of -1.
        id_: The ID of the node.
        fill_color: The fill color of the node.
        border_color: The border color of the node.
        border_width: The border width of the node.
    """
    index: int
    id_: str
    fill_color: wx.Colour
    border_color: wx.Colour
    border_width: float
    _position: Vec2
    _s_position: Vec2
    _size: Vec2
    _s_size: Vec2
    _scale: float

    # force keyword-only arguments
    def __init__(self, *, id_: str, pos: Vec2, size: Vec2, fill_color: wx.Colour,
                 border_color: wx.Colour, border_width: float, scale: float = 1, index: int = -1):
        self._scale = scale
        self.index = index
        self.id_ = id_
        self.position = pos
        self.size = size
        self.fill_color = fill_color
        self.border_color = border_color
        self.border_width = border_width

    @property
    def position(self):
        """The unscaled position of the node."""
        return self._position

    @position.setter
    def position(self, val: Vec2):
        self._position = val
        self._s_position = val * self._scale

    @property
    def s_position(self):
        """The scaled position of the node obtained by multiplying the scale."""
        return self._s_position

    @s_position.setter
    def s_position(self, val: Vec2):
        self._s_position = val
        self._position = val / self._scale

    @property
    def size(self):
        """The unscaled size of the node."""
        return self._size

    @size.setter
    def size(self, val: Vec2):
        self._size = val
        self._s_size = val * self._scale

    @property
    def s_size(self):
        """The scaled size of the node obtained by multiplying the scale."""
        return self._s_size

    @s_size.setter
    def s_size(self, val: Vec2):
        self._s_size = val
        self._size = val / self._scale

    @property
    def scale(self):
        """The scale of the rectangle. 1 by default."""
        return self._scale

    @scale.setter
    def scale(self, val: float):
        self._scale = val
        self._s_position = self._position * self._scale
        self._s_size = self._size * self._scale

    @property
    def s_rect(self):
        """Return scaled position/size as Rect.

        Note that the fields of the returned rect is copied, so one cannot modify this node through
        the rect.
        """
        return Rect(copy.copy(self.s_position), copy.copy(self.s_size))

    @property
    def rect(self):
        """The same as s_rect, but the rectangle is unscaled.
        """
        return Rect(copy.copy(self.position), copy.copy(self.size))


def rgba_to_wx_colour(rgb: int, alpha: float) -> wx.Colour:
    """Given RGBA color, return wx.Colour.
    
    Args:
        rgb: RGB color in hex format.
        alpha: The opacity of the color, ranging from 0.0 to 1.0.
    """
    b = rgb & 0xff
    g = (rgb >> 8) & 0xff
    r = (rgb >> 16) & 0xff
    return wx.Colour(r, g, b, int(alpha * 255))


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


def clamp_rect_size(rect: Rect, botright: Vec2, padding: int = 0) -> Vec2:
    """Clamp the size of the given rectangle if its bottom-right corner exceeds botright."""
    limit = botright - rect.position - Vec2.repeat(padding)
    assert limit.x > 0 and limit.y > 0

    return Vec2(min(limit.x, rect.size.x), min(limit.y, rect.size.y))


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


def convert_position(fn):
    """Decorator that converts the event position to one that is relative to the receiver."""

    def ret(self, evt):
        client_pos = evt.GetPosition()  # get raw position
        screen_pos = evt.EventObject.ClientToScreen(client_pos)  # convert to screen position
        relative_pos = self.ScreenToClient(screen_pos)  # convert to receiver position
        # call function
        copy = evt.Clone()
        copy.SetPosition(relative_pos)
        copy.foreign = not (self is evt.EventObject)
        fn(self, copy)
        evt.Skip()

    return ret


def get_nodes_by_idx(nodes: List[Node], indices: Collection[int]):
    """Simple helper that maps the given list of indices to their corresponding nodes."""
    ret = [n for n in nodes if n.index in indices]
    assert len(ret) == len(indices)
    return ret


def no_rzeros(num: float, precision: int) -> str:
    assert precision > 0
    fmt = '{:.' + str(precision) + 'f}'
    return fmt.format(num).rstrip('0').rstrip('.')


def on_msw() -> bool:
    """Returns whether we are running on Windows."""
    return os.name == 'nt'


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = getattr(sys, '_MEIPASS')
    else:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, 'resources', relative_path)
