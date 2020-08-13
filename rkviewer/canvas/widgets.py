"""Canvas widgets that are drawn within the canvas.
"""
# pylint: disable=maybe-no-member
import wx
import abc
import copy
from typing import Any, Callable, Dict, List, Optional
from .utils import draw_rect, get_bounding_rect, within_rect
from ..utils import Vec2, Rect, Node, clamp_point


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
    def OnPaint(self, gc: wx.GraphicsContext):
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

    def OnPaint(self, gc: wx.GraphicsContext):
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


class MultiSelect:
    """Class that manages selecting, moving, and resizing multiple nodes.
    
    This class will modify the position and size of the given list of nodes when the user
    interacts with the bounding rectangle. Therefore, a new MultiSelect should be constructed 
    whenever the passed list of nodes becomes outdated.
    """
    
    nodes: List[Node]
    _padding: float  #: padding for the bounding rectangle around the selected nodes
    _dragging: bool
    _resizing: bool
    _drag_rel: Vec2  #: relative position of the mouse to the bounding rect when dragging started
    _rel_positions: Optional[List[Vec2]]  #: relative positions of the nodes to the bounding rect
    _resize_handle: int  #: the node resize handle. See Canvas::_GetNodeResizeHandles for details.
    #: the minimum resize ratio for each axis, to avoid making the nodes too small
    _min_resize_ratio: Vec2
    _orig_rect: Optional[Rect]  #: the bounding rect when dragging/resizing started
    _bounds: Rect  #: the bounds that the bounding rect may not exceed
    _bounding_rect: Rect
    _theme: Dict[str, Any]  #: the current theme

    def __init__(self, nodes: List[Node], theme: Dict[str, Any], bounds: Rect):
        self.nodes = nodes
        # if only one node is selected, use the node padding instead
        self._padding = theme['select_box_padding'] if len(nodes) > 1 else \
            theme['node_outline_padding']
        rects = [n.s_rect for n in nodes]
        self._bounding_rect = get_bounding_rect(rects, self._padding)
        self._dragging = False
        self._resizing = False

        self._drag_rel = Vec2()
        self._rel_positions = None

        self._resize_handle = -1
        self._min_resize_ratio = Vec2()
        self._theme = theme
        self._orig_rect = None

        self._bounds = bounds

    @property
    def dragging(self):
        """Returns whether the user is drag-moving the bounding rectangle."""
        return self._dragging

    @property
    def resizing(self):
        """Returns whether the user is drag-resizing the bounding rectangle."""
        return self._resizing

    @property
    def bounding_rect(self):
        """The current bounding rectangle"""
        return self._bounding_rect

    def BeginDrag(self, mouse_pos: Vec2):
        """Begin a drag-moving operation."""
        assert not self._dragging
        assert not self._resizing
        self._dragging = True
        self._drag_rel = self._bounding_rect.position - mouse_pos
        self._rel_positions = [n.s_position - mouse_pos for n in self.nodes]

    def DoDrag(self, mouse_pos: Vec2):
        """Perform an ongoing drag-moving operation."""
        assert self._dragging

        new_positions = [mouse_pos + rp for rp in self._rel_positions]
        min_x = min(p.x for p in new_positions)
        min_y = min(p.y for p in new_positions)
        max_x = max(p.x + n.s_size.x for p, n in zip(new_positions, self.nodes))
        max_y = max(p.y + n.s_size.y for p, n in zip(new_positions, self.nodes))
        offset = Vec2(0, 0)

        lim_topleft = self._bounds.position
        lim_botright = self._bounds.position + self._bounds.size

        if min_x < lim_topleft.x:
            assert max_x <= lim_botright.x
            offset += Vec2(lim_topleft.x - min_x, 0)
        elif max_x > lim_botright.x:
            offset += Vec2(lim_botright.x - max_x, 0)

        if min_y < lim_topleft.y:
            assert max_y <= lim_botright.y
            offset += Vec2(0, lim_topleft.y - min_y)
        elif max_y > lim_botright.y:
            offset += Vec2(0, lim_botright.y - max_y)

        self._bounding_rect.position = mouse_pos + offset + self._drag_rel
        for node, np in zip(self.nodes, new_positions):
            node.s_position = np + offset

    def EndDrag(self):
        """End a drag-moving operation"""
        self._dragging = False

    def BeginResize(self, handle: int):
        """Begin a resizing operation on the given resize handle."""
        assert not self._dragging
        assert not self._resizing
        assert handle >= 0 and handle < 8

        self._resizing = True
        self._resize_handle = handle
        min_width = min(n.size.x for n in self.nodes)
        min_height = min(n.size.y for n in self.nodes)
        self._min_resize_ratio = Vec2(self._theme['min_node_width'] / min_width,
                                      self._theme['min_node_height'] / min_height)
        self._orig_rect = copy.copy(self._bounding_rect)
        self._orig_positions = [n.s_position - self._orig_rect.position - Vec2.repeat(self._padding)
                                for n in self.nodes]
        self._orig_sizes = [n.s_size for n in self.nodes]

    def DoResize(self, mouse_pos: Vec2):
        """Perform an ongoing resize operation."""
        assert self._resizing
        # STEP 1, get new rect vertices
        # see class comment for resize handle format. For side-handles, get the vertex in the
        # counter-clockwise direction
        dragged_idx = self._resize_handle // 2
        fixed_idx = int((dragged_idx + 2) % 4)  # get the vertex opposite dragged idx as fixed_idx
        orig_dragged_point = self._orig_rect.nth_vertex(dragged_idx)
        cur_dragged_point = self._bounding_rect.nth_vertex(dragged_idx)
        fixed_point = self._orig_rect.nth_vertex(fixed_idx)

        target_point = mouse_pos

        # if a side-handle, then only resize one axis
        if self._resize_handle % 2 == 1:
            if self._resize_handle % 4 == 1:
                # vertical resize; keep x the same
                target_point.x = orig_dragged_point.x
            else:
                assert self._resize_handle % 4 == 3
                target_point.y = orig_dragged_point.y

        # clamp target point
        target_point = clamp_point(target_point, self._bounds)

        # STEP 2, get and validate rect ratio

        # raw difference between (current/target) dragged vertex and fixed vertex. Raw as in this
        # is the visual difference shown on the bounding rect.
        orig_diff = orig_dragged_point - fixed_point
        target_diff = target_point - fixed_point

        signs = orig_diff.elem_mul(target_diff)

        # bounding_rect flipped?
        if signs.x < 0:
            target_point.x = cur_dragged_point.x

        if signs.y < 0:
            target_point.y = cur_dragged_point.y

        # take absolute value and subtract padding to get actual difference (i.e. sizing)
        pad_off = Vec2.repeat(self._padding)
        orig_size = (orig_dragged_point - fixed_point).elem_abs() - pad_off * 2
        target_size = (target_point - fixed_point).elem_abs() - pad_off * 2

        size_ratio = target_size.elem_div(orig_size)

        # size too small?
        if size_ratio.x < self._min_resize_ratio.x:
            size_ratio = size_ratio.swapped(0, self._min_resize_ratio.x)
            target_point.x = cur_dragged_point.x

        if size_ratio.y < self._min_resize_ratio.y:
            size_ratio = size_ratio.swapped(1, self._min_resize_ratio.y)
            target_point.y = cur_dragged_point.y

        # re-calculate target_size in case size_ratio changed
        target_size = orig_size.elem_mul(size_ratio)

        # STEP 3 calculate new bounding_rect position and size
        br_pos = Vec2(min(fixed_point.x, target_point.x),
                      min(fixed_point.y, target_point.y))

        # STEP 4 calculate and apply new node positions and sizes
        for node, orig_pos, orig_size in zip(self.nodes, self._orig_positions, self._orig_sizes):
            assert orig_pos.x >= -1e-6 and orig_pos.y >= -1e-6
            node.s_position = br_pos + orig_pos.elem_mul(size_ratio) + pad_off
            node.s_size = orig_size.elem_mul(size_ratio)

        # STEP 5 apply new bounding_rect position and size
        self._bounding_rect.position = br_pos
        self._bounding_rect.size = target_size + pad_off * 2

    def EndResize(self):
        """End a resize operation."""
        self._resizing = False
