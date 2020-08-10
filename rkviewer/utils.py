"""Utility functions"""
from __future__ import annotations  # For returning self in a class
# pylint: disable=maybe-no-member
import wx
import copy
from typing import Callable, Tuple, TypeVar


TNum = TypeVar('TNum', float, int)


class Vec2:
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

    def to_wx_point(self) -> wx.Point:
        return wx.Point(self.x, self.y)

    # element-wise multiplication
    def elem_mul(self, other: Vec2) -> Vec2:
        return Vec2(self.x * other.x, self.y * other.y)

    def elem_div(self, other: Vec2) -> Vec2:
        return Vec2(self.x / other.x, self.y / other.y)

    def elem_abs(self) -> Vec2:
        return Vec2(abs(self.x), abs(self.y))

    def map(self, op: Callable) -> Vec2:
        return Vec2(op(self.x), op(self.y))

    @classmethod
    def repeat(cls, val: TNum = 1) -> Vec2:
        return Vec2(val, val)


class Rect:
    def __init__(self, pos: Vec2, size: Vec2):
        self.position = pos
        self.size = size

    def GetTuple(self) -> Tuple[Vec2, Vec2]:
        return (self.position, self.size)

    def NthVertex(self, n: int):
        if n == 0:
            return self.position
        elif n == 1:
            return self.position + Vec2(self.size.x, 0)
        elif n == 2:
            return self.position + self.size
        elif n == 3:
            return self.position + Vec2(0, self.size.y)
        else:
            assert False, "Rect.NthVertex() index out of bounds"

    def __repr__(self):
        return 'Rect({}, {})'.format(self.position, self.size)


class Node:
    id_: str
    _position: Vec2
    _s_position: Vec2  # scaled position # TODO add documentation
    _size: Vec2
    _s_size: Vec2  # scaled size
    fill_color: wx.Colour
    border_color: wx.Colour
    border_width: float
    _scale: float

    # force keyword-only arguments
    def __init__(self, *, id_: str, pos: Vec2, size: Vec2, fill_color: wx.Colour,
                 border_color: wx.Colour, border_width: float, scale: float = 1):
        self._scale = scale
        self.id_ = id_
        self.position = pos
        self.size = size
        self.fill_color = fill_color
        self.border_color = border_color
        self.border_width = border_width

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, val: Vec2):
        self._position = val
        self._s_position = val * self._scale

    @property
    def s_position(self):
        return self._s_position

    @s_position.setter
    def s_position(self, val: Vec2):
        self._s_position = val
        self._position = val / self._scale

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, val: Vec2):
        self._size = val
        self._s_size = val * self._scale

    @property
    def s_size(self):
        return self._s_size

    @s_size.setter
    def s_size(self, val: Vec2):
        self._s_size = val
        self._size = val / self._scale

    @property
    def scale(self):
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


def IodToWxColour(rgb: int, alpha: float):
    b = rgb & 0xff
    g = (rgb >> 8) & 0xff
    r = (rgb >> 16) & 0xff
    return wx.Colour(r, g, b, int(alpha * 255))



def convert_position(fn):
    """Decorator that converts event position to one that is relative to the receiver."""
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
