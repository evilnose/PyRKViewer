"""Canvas utilities, including overlays like the minimap and the drag n' drop.
"""
# pylint: disable=maybe-no-member
import wx
import abc
import copy
from math import copysign
from typing import Any, Callable, Dict, List
from .types import Vec2, Rect, Node
from .utils import ClampPoint, DrawRect, GetBoundingRect, WithinRect


class CanvasOverlay(abc.ABC):
    _size: Vec2
    _position: Vec2

    @property
    def size(self):
        return self._size

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, val: Vec2):
        self._position = val

    @abc.abstractmethod
    def OnPaint(self, gc: wx.GraphicsContext):
        pass

    @abc.abstractmethod
    def OnLeftDown(self, evt: wx.MouseEvent):
        pass

    @abc.abstractmethod
    def OnLeftUp(self, evt: wx.MouseEvent):
        pass

    @abc.abstractmethod
    def OnMotion(self, evt: wx.MouseEvent):
        pass


class Minimap(CanvasOverlay):
    """Class for drawing a minimap and handling its data and events.

    This is not a subclass of wx.Panel, since semi-transparent background is needed.
    """
    Callback = Callable[[Vec2], None]

    _realsize: Vec2  # real size of the canvas
    window_pos: Vec2  # position of the canvas window (visible part)
    window_size: Vec2  # size of the canvas window (visible part)
    _width: int
    nodes: List[Node]
    _callback: Callback
    _dragging: bool  # whether the visible window handle is being dragged
    # Position of the mouse relative to the top-left corner of the visible window handle on minimap.
    # We keep this relative distance invariant when dragging. This is used because scrolling is
    # discrete, so we cannot add relative distance dragged since errors will accumulate.
    _drag_pos: Vec2

    def __init__(self, *, pos: Vec2 = Vec2(), width: int, realsize: Vec2, window_pos: Vec2,
                 window_size: Vec2, pos_callback: Callback):
        self._position = pos
        self._width = width
        self.realsize = realsize  # use the setter to set the _size as well
        self.window_pos = window_pos
        self.window_size = window_size
        self.nodes = list()
        self._callback = pos_callback
        self._dragging = False
        self._drag_pos = Vec2()

    @property
    def realsize(self):
        return self._realsize

    @realsize.setter
    def realsize(self, val: Vec2):
        self._realsize = val
        self._size = Vec2(self._width, self._width * val.y / val.x)

    @property
    def dragging(self):
        return self._dragging

    def OnPaint(self, gc: wx.GraphicsContext):
        scale = self._size.x / self._realsize.x

        # draw total rect TODO color
        DrawRect(gc, Rect(self.position, self._size), fill=wx.Colour(150, 150, 150, 100))
        my_botright = self.position + self._size

        win_pos = self.window_pos * scale + self.position
        win_size = self.window_size * scale

        # clip window size
        win_size.x = min(win_size.x, my_botright.x - win_pos.x)
        win_size.y = min(win_size.y, my_botright.y - win_pos.y)

        # draw visible rect
        DrawRect(gc, Rect(win_pos, win_size), fill=wx.Colour(255, 255, 255, 130))

        # draw nodes
        for node in self.nodes:
            n_pos = node.position * scale + self.position
            n_size = node.size * scale
            fc = node.fill_color
            color = wx.Colour(fc.Red(), fc.Green(), fc.Blue(), 100)
            DrawRect(gc, Rect(n_pos, n_size), fill=color)

    def OnLeftDown(self, evt: wx.Event):
        if not self._dragging:
            scale = self._size.x / self._realsize.x
            pos = Vec2(evt.GetPosition()) - self.position
            if WithinRect(pos, Rect(self.window_pos * scale, self.window_size * scale)):
                self._dragging = True
                self._drag_pos = pos - self.window_pos * scale
            else:
                topleft = pos - self.window_size * scale / 2
                self._callback(topleft / scale)

    def OnLeftUp(self, evt: wx.Event):
        self._dragging = False

    def OnMotion(self, evt: wx.MouseEvent):
        scale = self._size.x / self._realsize.x
        pos = Vec2(evt.GetPosition()) - self.position
        pos = ClampPoint(pos, Rect(Vec2(), self.size))
        if evt.LeftIsDown():
            if not self._dragging:
                topleft = pos - self.window_size * scale / 2
                self._callback(topleft / scale)
            else:
                actual_pos = pos - self._drag_pos
                self._callback(actual_pos / scale)


class MultiSelect:
    def __init__(self, nodes: List[Node], theme: Dict[str, Any], bounds: Rect):
        self._nodes = nodes
        # if only one node is selected, use the node padding instead
        self._padding = theme['select_box_padding'] if len(nodes) > 1 else \
            theme['node_outline_padding']
        self.bounding_rect = GetBoundingRect(nodes, self._padding)
        self._dragging = False
        self._resizing = False

        self._drag_rel = Vec2()
        self._rel_positions = None

        self._resize_handle = -1
        self._min_resize_ratio = Vec2()
        self.theme = theme
        self._orig_rect = None

        self._bounds = bounds

    @property
    def dragging(self):
        return self._dragging

    @property
    def resizing(self):
        return self._resizing

    @property
    def nodes(self):
        return self._nodes

    def refresh_nodes(self, nodes: List[Node]):
        """Called when user hasn't stopped dragging but the nodes have been updated.
        """
        self._nodes = nodes

    def BeginDrag(self, mouse_pos: Vec2):
        assert not self._dragging
        assert not self._resizing
        self._dragging = True
        self._drag_rel = self.bounding_rect.position - mouse_pos
        self._rel_positions = [n.s_position - mouse_pos for n in self._nodes]

    def DoDrag(self, mouse_pos: Vec2):
        assert self._dragging

        new_positions = [mouse_pos + rp for rp in self._rel_positions]
        min_x = min(p.x for p in new_positions)
        min_y = min(p.y for p in new_positions)
        max_x = max(p.x + n.s_size.x for p, n in zip(new_positions, self._nodes))
        max_y = max(p.y + n.s_size.y for p, n in zip(new_positions, self._nodes))
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

        self.bounding_rect.position = mouse_pos + offset + self._drag_rel
        for node, np in zip(self._nodes, new_positions):
            node.s_position = np + offset
        '''
        x_good = True  # x-axis in bounds
        y_good = True  # y-axis in bounds
        for node, np in zip(self._nodes, new_positions):
            botright = np + node.s_size
            if x_good and np.x < lim_topleft.x or botright.x > lim_botright.x:
                x_good = False
            if y_good and np.y < lim_topleft.y or botright.y > lim_botright.y:
                y_good = False

        for axis, good in enumerate([x_good, y_good]):
            if good:
                self.bounding_rect.position = self.bounding_rect.position.swapped(
                    axis, mouse_pos[axis] + self._drag_rel[axis])
        '''

    def EndDrag(self):
        self._dragging = False

    def BeginResize(self, handle: int):
        assert not self._dragging
        assert not self._resizing
        assert handle >= 0 and handle < 8

        self._resizing = True
        self._resize_handle = handle
        min_width = min(n.size.x for n in self.nodes)
        min_height = min(n.size.y for n in self.nodes)
        self._min_resize_ratio = Vec2(self.theme['min_node_width'] / min_width,
                                      self.theme['min_node_height'] / min_height)
        self._orig_rect = copy.copy(self.bounding_rect)
        self._orig_positions = [n.s_position - self._orig_rect.position - Vec2.repeat(self._padding)
                                for n in self._nodes]
        self._orig_sizes = [n.s_size for n in self._nodes]

    def DoResize(self, mouse_pos: Vec2):
        assert self._resizing
        # STEP 1, get new rect vertices
        # see class comment for resize handle format. For side-handles, get the vertex in the
        # counter-clockwise direction
        dragged_idx = self._resize_handle // 2
        fixed_idx = int((dragged_idx + 2) % 4)  # get the vertex opposite dragged idx as fixed_idx
        orig_dragged_point = self._orig_rect.NthVertex(dragged_idx)
        cur_dragged_point = self.bounding_rect.NthVertex(dragged_idx)
        fixed_point = self._orig_rect.NthVertex(fixed_idx)

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
        target_point = ClampPoint(target_point, self._bounds)

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
        for node, orig_pos, orig_size in zip(self._nodes, self._orig_positions, self._orig_sizes):
            assert orig_pos.x >= -1e-6 and orig_pos.y >= -1e-6
            node.s_position = br_pos + orig_pos.elem_mul(size_ratio) + pad_off
            node.s_size = orig_size.elem_mul(size_ratio)

        # STEP 5 apply new bounding_rect position and size
        self.bounding_rect.position = br_pos
        self.bounding_rect.size = target_size + pad_off * 2

    def EndResize(self):
        self._resizing = False
