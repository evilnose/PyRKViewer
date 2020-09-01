"""Canvas widgets that are drawn within the canvas.
"""
# pylint: disable=maybe-no-member
import wx
import abc
from typing import Callable, List
from .data import Node
from .geometry import Vec2, Rect, clamp_point, within_rect
from .utils import draw_rect


class CanvasOverlay(abc.ABC):
    """Abstract class for a fixed-position overlay within the canvas.
    
    Attributes:
        hovering: Used to set whether the mouse is current hovering over the overlay.
    """
    hovering: bool
    _size: Vec2  #: Private attribute for the 'size' property.
    _position: Vec2  #: Private attribute for the 'position' property.

    @property
    def size(self) -> Vec2:
        """Return the size (i.e. of a rectangle) of the overlay."""
        return self._size

    @property
    def position(self) -> Vec2:
        """Return the position (i.e. of the top-left corner) of the overlay."""
        return self._position

    @position.setter
    def position(self, val: Vec2):
        self._position = val

    @abc.abstractmethod
    def DoPaint(self, gc: wx.GraphicsContext):
        """Re-paint the overlay."""
        pass

    @abc.abstractmethod
    def OnLeftDown(self, evt: wx.MouseEvent):
        """Trigger a mouse left button down event on the overlay."""
        pass

    @abc.abstractmethod
    def OnLeftUp(self, evt: wx.MouseEvent):
        """Trigger a mouse left button up event on the overlay."""
        pass

    @abc.abstractmethod
    def OnMotion(self, evt: wx.MouseEvent):
        """Trigger a mouse motion event on the overlay."""
        pass


class Minimap(CanvasOverlay):
    """The minimap class that derives from CanvasOverlay.
    
    Attributes:
        Callback: Type of the callback function called when the position of the minimap changes.

        window_pos: Position of the canvas window, as updated by canvas.
        window_size: Size of the canvas window, as updated by canvas.
        nodes: The current list of nodes, as updated by canvas.
    """
    Callback = Callable[[Vec2], None]
    window_pos: Vec2
    
    window_size: Vec2
    nodes: List[Node]

    _realsize: Vec2
    _width: int
    _callback: Callback #: the function called when the minimap position changes
    _dragging: bool
    _drag_rel: Vec2
    """Position of the mouse relative to the top-left corner of the visible window handle on
    minimap, the moment when dragging starts. We keep this relative distance invariant while
    dragging. This is used because scrolling is discrete, so we cannot add relative distance
    dragged since errors will accumulate.
    """


    def __init__(self, *, pos: Vec2, width: int, realsize: Vec2, window_pos: Vec2 = Vec2(),
                 window_size: Vec2, pos_callback: Callback):
        """The constructor of the minimap

        Args:
            pos: The position of the minimap relative to the top-left corner of the canvas window.
            width: The width of the minimap. The height will be set according to perspective.
            realsize: The actual, full size of the canvas.
            window_pos: The starting position of the window.
            window_size: The starting size of the window.
            pos_callback: The callback function called when the minimap window changes position.
        """
        self._position = pos
        self._width = width
        self.realsize = realsize  # use the setter to set the _size as well
        self.window_pos = window_pos
        self.window_size = window_size
        self.nodes = list()
        self._callback = pos_callback
        self._dragging = False
        self._drag_rel = Vec2()
        self.hovering = False

    @property
    def realsize(self):
        """The actual, full size of the canvas, including those not visible on screen."""
        return self._realsize

    @realsize.setter
    def realsize(self, val: Vec2):
        self._realsize = val
        self._size = Vec2(self._width, self._width * val.y / val.x)

    @property
    def dragging(self):
        """Whether the user is current dragging on the minimap window."""
        return self._dragging

    def DoPaint(self, gc: wx.GraphicsContext):
        # TODO move this somewhere else
        BACKGROUND_USUAL = wx.Colour(155, 155, 155, 50)
        FOREGROUND_USUAL = wx.Colour(255, 255, 255, 100)
        BACKGROUND_FOCUS = wx.Colour(155, 155, 155, 80)
        FOREGROUND_FOCUS = wx.Colour(255, 255, 255, 130)
        FOREGROUND_DRAGGING = wx.Colour(255, 255, 255, 200)

        background = BACKGROUND_FOCUS if (self.hovering or self._dragging) else BACKGROUND_USUAL
        foreground = FOREGROUND_USUAL
        if self._dragging:
            foreground = FOREGROUND_DRAGGING
        elif self.hovering:
            foreground = FOREGROUND_FOCUS

        scale = self._size.x / self._realsize.x

        # draw total rect
        draw_rect(gc, Rect(self.position, self._size), fill=background)
        my_botright = self.position + self._size

        win_pos = self.window_pos * scale + self.position
        win_size = self.window_size * scale

        # clip window size
        win_size.x = min(win_size.x, my_botright.x - win_pos.x)
        win_size.y = min(win_size.y, my_botright.y - win_pos.y)

        # draw visible rect
        draw_rect(gc, Rect(win_pos, win_size), fill=foreground)

        # draw nodes
        for node in self.nodes:
            n_pos = node.position * scale + self.position
            n_size = node.size * scale
            fc = node.fill_color
            color = wx.Colour(fc.Red(), fc.Green(), fc.Blue(), 100)
            draw_rect(gc, Rect(n_pos, n_size), fill=color)

    def OnLeftDown(self, evt: wx.Event):
        if not self._dragging:
            scale = self._size.x / self._realsize.x
            pos = Vec2(evt.GetPosition()) - self.position
            if within_rect(pos, Rect(self.window_pos * scale, self.window_size * scale)):
                self._dragging = True
                self._drag_rel = pos - self.window_pos * scale
            else:
                topleft = pos - self.window_size * scale / 2
                self._callback(topleft / scale)

    def OnLeftUp(self, evt: wx.Event):
        self._dragging = False

    def OnMotion(self, evt: wx.MouseEvent):
        scale = self._size.x / self._realsize.x
        pos = Vec2(evt.GetPosition()) - self.position
        pos = clamp_point(pos, Rect(Vec2(), self.size))
        if evt.LeftIsDown():
            if not self._dragging:
                topleft = pos - self.window_size * scale / 2
                self._callback(topleft / scale)
            else:
                actual_pos = pos - self._drag_rel
                self._callback(actual_pos / scale)
