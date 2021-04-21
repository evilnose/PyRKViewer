"""Widgets that are floating on top of the canvas (overlaid) which do not change position on scroll.
"""
# pylint: disable=maybe-no-member
from sortedcontainers.sortedlist import SortedKeyList
from rkviewer.canvas.elements import CanvasElement, CompartmentElt, NodeElement
from rkviewer.canvas.state import cstate
from rkviewer.config import Color
import wx
import abc
from typing import Callable, List, cast
from .geometry import Vec2, Rect, clamp_point, pt_in_rect
from .utils import draw_rect


class CanvasOverlay(abc.ABC):
    """Abstract class for a fixed-position overlay within the canvas.
    
    Attributes:
        hovering: Used to set whether the mouse is current hovering over the overlay.

    Note:
        Overlays use device positions since it makes the most sense for these static items.
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
    def OnLeftDown(self, device_pos: Vec2):
        """Trigger a mouse left button down event on the overlay."""
        pass

    @abc.abstractmethod
    def OnLeftUp(self, device_pos: Vec2):
        """Trigger a mouse left button up event on the overlay."""
        pass

    @abc.abstractmethod
    def OnMotion(self, device_pos: Vec2, is_down: bool):
        """Trigger a mouse motion event on the overlay."""
        pass


# TODO refactor this as a CanvasElement and delete this file
class Minimap(CanvasOverlay):
    """The minimap class that derives from CanvasOverlay.
    
    Attributes:
        Callback: Type of the callback function called when the position of the minimap changes.

        window_pos: Position of the canvas window, as updated by canvas.
        window_size: Size of the canvas window, as updated by canvas.
        device_pos: The device position (i.e. seen on screen) of the top left corner. Used for
                    determining user click/drag offset. It is important to use the device_pos,
                    since it does not change, whereas window_pos (logical position) changes based
                    on scrolling. This coupled with delays in update causes very noticeable jitters
                    when dragging.
        elements: The list of elements updated by canvas.
    """
    Callback = Callable[[Vec2], None]
    window_pos: Vec2
    window_size: Vec2
    device_pos: Vec2
    elements: SortedKeyList
    _position: Vec2  #: Unscrolled, i.e. logical position of the minimap. This varies by scrolling.
    _realsize: Vec2  #: Full size of the canvas
    _width: int
    _callback: Callback #: the function called when the minimap position changes
    _dragging: bool
    _drag_rel: Vec2
    """Position of the mouse relative to the top-left corner of the visible window handle on
    minimap, the moment when dragging starts. We keep this relative distance invariant while
    dragging. This is used because scrolling is discrete, so we cannot add relative distance
    dragged since errors will accumulate.
    """


    def __init__(self, *, pos: Vec2, device_pos: Vec2, width: int, realsize: Vec2, window_pos: Vec2 = Vec2(),
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
        self.device_pos = device_pos  # should stay fixed
        self._width = width
        self.realsize = realsize  # use the setter to set the _size as well
        self.window_pos = window_pos
        self.window_size = window_size
        self.elements = SortedKeyList()
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

        draw_rect(gc, Rect(self.position, self._size), fill=background)
        my_botright = self.position + self._size

        win_pos = self.window_pos * scale + self.position
        win_size = self.window_size * scale

        # clip window size
        span = my_botright - win_pos
        win_size = win_size.reduce2(min, span)

        # draw visible rect
        draw_rect(gc, Rect(win_pos, win_size), fill=foreground)

        for el in self.elements:
            pos: Vec2
            size: Vec2
            fc: wx.Colour
            if isinstance(el, NodeElement):
                el = cast(NodeElement, el)
                pos = el.node.position * scale + self.position
                size = el.node.size * scale
                fc = (el.node.fill_color or Color(128, 128, 128)).to_wxcolour()
            elif isinstance(el, CompartmentElt):
                el = cast(CompartmentElt, el)
                pos = el.compartment.position * scale + self.position
                size = el.compartment.size * scale
                fc = el.compartment.fill
            else:
                continue

            color = wx.Colour(fc.Red(), fc.Green(), fc.Blue(), 100)
            draw_rect(gc, Rect(pos, size), fill=color)


    def OnLeftDown(self, device_pos: Vec2):
        if not self._dragging:
            scale = self._size.x / self._realsize.x
            pos = device_pos - self.device_pos
            if pt_in_rect(pos, Rect(self.window_pos * scale, self.window_size * scale)):
                self._dragging = True
                self._drag_rel = pos - self.window_pos * scale
            else:
                topleft = pos - self.window_size * scale / 2
                self._callback(topleft / scale * cstate.scale)

    def OnLeftUp(self, _: Vec2):
        self._dragging = False

    def OnMotion(self, device_pos: Vec2, is_down: bool):
        scale = self._size.x / self._realsize.x
        pos = device_pos - self.device_pos
        pos = clamp_point(pos, Rect(Vec2(), self.size))
        if is_down:
            if not self._dragging:
                topleft = pos - self.window_size * scale / 2
                self._callback(topleft / scale * cstate.scale)
            else:
                actual_pos = pos - self._drag_rel
                self._callback(actual_pos / scale * cstate.scale)
