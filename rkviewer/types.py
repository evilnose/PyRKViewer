from __future__ import annotations  # For returning self in a class
from typing import NewType, List, Tuple
import abc
import copy
# pylint: disable=maybe-no-member
import wx


class Vec2:
    x: int
    y: int
    _i: int

    def __init__(self, x, y=None):
        """Initialize a 2D vector.

        If two arguments are specified, they are considered the x and y coordinate
        of the Vec2.

        If only one argument is specified, it should be an iterable of two elements,
        which will be unwrapped as x and y.
        """
        if y is None:
            self.x, self.y = x
        else:
            self.x = x
            self.y = y
            self._i = 0

    def __iter__(self) -> Vec2:
        self._i = 0
        return self

    def __next__(self) -> int:
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

    def __iadd__(self, other) -> Vec2:
        self.x += other.x
        self.y += other.y
        return self

    def __sub__(self, other) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __isub__(self, other) -> Vec2:
        self.x -= other.x
        self.y -= other.y
        return self

    def __mul__(self, k) -> Vec2:
        return Vec2(self.x * k, self.y * k)

    __rmul__ = __mul__

    def __imul__(self, k) -> Vec2:
        self.x = self.x * k
        self.y *= self.y * k
        return self

    def __truediv__(self, k) -> Vec2:
        return Vec2(self.x / k, self.y / k)

    def __repr__(self) -> str:
        return 'Vec2({}, {})'.format(self.x, self.y)

    def to_wx_point(self) -> wx.Point:
        return wx.Point(self.x, self.y)

    # element-wise multiplication
    def elem_mul(self, other: Vec2) -> Vec2:
        return Vec2(self.x * other.x, self.y * other.y)

    def elem_div(self, other: Vec2) -> Vec2:
        return Vec2(self.x / other.x, self.y / other.y)

    def elem_abs(self) -> Vec2:
        return Vec2(abs(self.x), abs(self.y))

    @classmethod
    def unity(cls) -> Vec2:
        return Vec2(1, 1)


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


class Node:
    id_: str
    _position: Vec2
    _s_position: Vec2  # scaled position # TODO add documentation
    _size: Vec2
    _s_size: Vec2  # scaled size
    fill_color: wx.Colour
    border_color: wx.Colour
    border_width: int
    _scale: float

    # force keyword-only arguments
    def __init__(self, *, id_: str, pos: Vec2, size: Vec2, fill_color: wx.Colour,
                 border_color: wx.Colour, border_width: int, scale: float = 1):
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

    '''
    def as_rect(self) -> Rect:
        """Return scaled position/size as Rect"""
        return Rect(copy.copy(self.s_position), copy.copy(self.s_size))
    '''

DEFAULT_THEME = {
    'canvas_bg': wx.WHITE,
    'toolbar_bg': wx.Colour(140, 140, 140),
    'canvas_width': 600,
    'canvas_height': 500,
    'left_toolbar_width': 100,
    'top_toolbar_height': 40,
    'node_fill': wx.Colour(0, 255, 0, 50),
    'node_border': wx.Colour(255, 0, 0, 100),
    'node_width': 50,
    'node_height': 30,
    'node_border_width': 1,
    'node_font_size': 10,  # TODO
    'node_font_color': wx.Colour(255, 0, 0, 100),  # TODO
    'node_outline_color': wx.Colour(0, 140, 255),  # Distance from node to its (selection) outline
    'node_outline_padding': 7,  # Distance from node to its (selection) outline
    'node_handle_length': 8,  # Length of the squares one uses to drag resize nodes
    'node_outline_width': 1.8,  # Width of the selected node outline
    'init_scale': 1,
    'min_node_width': 20,
    'min_node_height': 15,
}


class IController(abc.ABC):
    """The inteface class for a controller

    The abc.ABC (Abstract Base Class) is used to enforce the MVC interface more
    strictly.

    The methods with name beginning with Try- are usually called by the View after
    some user input. If the action tried in such a method succeeds, the Controller
    should request the view to be redrawn
    """

    @abc.abstractmethod
    def TryAddNode(self, node: Node):
        """Try to add the given Node to the canvas."""
        pass

    @abc.abstractmethod
    def TryMoveNode(self, id_: str, pos: Vec2):
        """Try to move the give node. TODO only accept node ID and new location"""
        pass

    @abc.abstractmethod
    def TrySetNodeSize(self, id_: str, size: Vec2):
        """Try to move the give node. TODO only accept node ID and new location"""
        pass

    @abc.abstractmethod
    def GetListOfNodeIds(self) -> List[str]:
        """Try getting the list of node IDs"""
        pass


class IView(abc.ABC):
    """The inteface class for a controller

    The abc.ABC (Abstract Base Class) is used to enforce the MVC interface more
    strictly.
    """

    @abc.abstractmethod
    def BindController(self, controller: IController):
        """Bind the controller. This needs to be called after a controller is 
        created and before any other method is called.
        """
        pass

    @abc.abstractmethod
    def MainLoop(self):
        """Run the main loop. This is blocking right now. This may be modified to
        become non-blocking in the future if required.
        """
        pass

    @abc.abstractmethod
    def UpdateAll(self, nodes):
        """Update all the graph objects, and redraw everything at the end"""
        pass
