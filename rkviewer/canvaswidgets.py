"""Overlaid widgets on canvas, including the minimap and the drag n' drop.
"""
# pylint: disable=maybe-no-member
import wx
import abc
from typing import Callable, List
from .types import Vec2, Rect, Node
from .utils import DrawRect


class CanvasOverlay(abc.ABC):
    @property
    @abc.abstractmethod
    def size(self):
        pass

    @property
    @abc.abstractmethod
    def position(self):
        pass

    @abc.abstractmethod
    def OnLeftDown(self, evt: wx.MouseEvent):
        pass

    @abc.abstractmethod
    def OnMotion(self, evt: wx.MouseEvent):
        pass


class Minimap(CanvasOverlay):
    """Class for drawing a minimap and handling its data and events.

    This is not a subclass of wx.Panel, since semi-transparent background is needed.
    """
    Callback = Callable[[Vec2], None]

    _position: Vec2
    _realsize: Vec2  # real size of the canvas
    window_pos: Vec2  # position of the canvas window (visible part)
    window_size: Vec2  # size of the canvas window (visible part)
    _size: Vec2
    _width: int
    nodes: List[Node]
    _callback : Callback

    def __init__(self, *, pos: Vec2 = Vec2(0, 0), width: int, realsize: Vec2, window_pos: Vec2,
                 window_size: Vec2, pos_callback: Callback):
        self._position = pos
        self._width = width
        self.realsize = realsize  # use the setter to set the _size as well
        self.window_pos = window_pos
        self.window_size = window_size
        self.nodes = list()
        self._callback = pos_callback

    @property
    def realsize(self):
        return self._realsize

    @realsize.setter
    def realsize(self, val: Vec2):
        self._realsize = val
        self._size = Vec2(self._width, self._width * val.y / val.x)

    @property
    def size(self):
        return self._size

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, val: Vec2):
        self._position = val

    def Paint(self, gc: wx.GraphicsContext):
        scale = self._size.x / self._realsize.x

        # draw total rect
        DrawRect(gc, Rect(self.position, self._size), wx.Colour(150, 150, 150, 100))
        my_botright = self.position + self._size

        win_pos = self.window_pos * scale + self.position
        win_size = self.window_size * scale

        # clip window size
        win_size.x = min(win_size.x, my_botright.x - win_pos.x)
        win_size.y = min(win_size.y, my_botright.y - win_pos.y)

        # draw visible rect
        DrawRect(gc, Rect(win_pos, win_size), wx.Colour(255, 255, 255, 130))

        # draw nodes
        for node in self.nodes:
            n_pos = node.position * scale + self.position
            n_size = node.size * scale
            fc = node.fill_color
            color = wx.Colour(fc.Red(), fc.Green(), fc.Blue(), 100)
            DrawRect(gc, Rect(n_pos, n_size), color)

    def OnLeftDown(self, evt: wx.Event):
        scale = self._realsize.x / self._size.x
        center = (Vec2(evt.GetPosition()) - self.position) * scale
        self._callback(center - self.window_size / 2)
        
    def OnMotion(self, evt: wx.MouseEvent):
        if evt.LeftIsDown():
            scale = self._realsize.x / self._size.x
            center = (Vec2(evt.GetPosition()) - self.position) * scale
            self._callback(center - self.window_size / 2)
