from __future__ import annotations  # For referencing self in a class
# pylint: disable=maybe-no-member
import enum
from itertools import chain
from rkviewer.canvas.events import EVT_C_MOVE_NODE, EVT_NODE_DID_MOVE
from rkviewer.mvc import IController
import wx
from abc import abstractmethod
import bisect
from typing import Any, Callable, Iterator, List, Optional
from .data import Node, BezierHandle, Reaction, ToScrolledFn
from .geometry import Rect, Vec2, clamp_point, get_bounding_rect, padded_rect, within_rect
from .state import cstate
from .utils import draw_rect
from ..config import settings, theme


ToScrolledFn = Callable[[Vec2], Vec2]
SetCursorFn = Callable[[wx.Cursor], None]


class CanvasElement:
    """Base class for an element positioned on the canvas.

    Attributes:
        layer: The layer number of this element.
        to_scrolled_fn: Function for converting logical to scrolled (device) position.
                        TODO move this out as a module-level function.
    """
    layer: int
    to_scrolled_fn: ToScrolledFn

    def __init__(self, to_scrolled_fn: ToScrolledFn, layer: int):
        self.layer = layer
        self.to_scrolled_fn = to_scrolled_fn

    @abstractmethod
    def pos_inside(self, logical_pos: Vec2) -> bool:
        """Returns whether logical_pos is inside the diplayed shape of this element."""
        pass

    @abstractmethod
    def do_paint(self, gc: wx.GraphicsContext):
        """Paint the shape onto the given GraphicsContext."""
        pass

    def do_mouse_enter(self, logical_pos: Vec2) -> bool:
        """Handler for when the mouse has entered the shape."""
        return False

    def do_mouse_leave(self, logical_pos: Vec2) -> bool:
        """Handler for when the mouse has exited the shape"""
        return False

    def do_mouse_move(self, logical_pos: Vec2) -> bool:
        """Handler for when the mouse moves inside the shape, with the left mouse button up."""
        return False

    def do_mouse_drag(self, logical_pos: Vec2, rel_pos: Vec2) -> bool:
        """Handler for when the mouse drags inside the shape, with the left mouse button down."""
        return False

    def do_left_down(self, logical_pos: Vec2) -> bool:
        """Handler for when the mouse left button is pressed down inside the shape."""
        return False

    def do_left_up(self, logical_pos: Vec2) -> bool:
        """Handler for when the mouse left button is springs up inside the shape."""
        return False

    def to_scrolled_rect(self, rect: Rect):
        """Helper that converts rectangle to scrolled (device) position."""
        adj_pos = Vec2(self.to_scrolled_fn(rect.position))
        return Rect(adj_pos, rect.size)


# TODO add option to change layer of element
class LayeredElements:
    """Class that keeps track of layered canvas elements.

    Attributes:
        keys: Sorted list of the layer numbers of the elements; matches 1-1 with elements.
        elements: List of CanvasElements; match 1-1 with keys.
    """
    keys: List[int]
    elements: List[CanvasElement]

    def __init__(self, elements=list()):
        self.keys = list()
        self.elements = list()
        for el in elements:
            self.add(el)

    def add(self, el: CanvasElement):
        k = el.layer
        idx = bisect.bisect_right(self.keys, k)
        self.keys.insert(idx, k)
        self.elements.insert(idx, el)

    def bottom_up(self) -> Iterator[CanvasElement]:
        """Returns an iterator from the bottom to the top layer.

        In the same layer, elements are returned in the original order they were added.
        """
        return iter(self.elements)

    def top_down(self) -> Iterator[CanvasElement]:
        """Returns an iterator from the top to the bottom layer.

        In the same layer, elements are returned in the reverse order they were added.
        """
        return reversed(self.elements)


class NodeElement(CanvasElement):
    """CanvasElement for nodes."""
    node: Node
    canvas: Any

    # HACK no type for canvas since otherwise there would be circular dependency
    def __init__(self, node: Node, canvas, to_scrolled_fn: ToScrolledFn, layer: int):
        super().__init__(to_scrolled_fn, layer)
        self.node = node
        self.canvas = canvas

    def pos_inside(self, logical_pos: Vec2) -> bool:
        return within_rect(logical_pos, self.node.s_rect)

    def do_paint(self, gc: wx.GraphicsContext):
        font = wx.Font(wx.FontInfo(10 * cstate.scale))
        gfont = gc.CreateFont(font, wx.BLACK)
        gc.SetFont(gfont)

        scrolled_pos = self.to_scrolled_fn(self.node.s_position)
        width, height = self.node.s_size
        border_width = self.node.border_width * cstate.scale

        draw_rect(
            gc,
            Rect(scrolled_pos, self.node.s_size),
            fill=self.node.fill_color,
            border=self.node.border_color,
            border_width=border_width,
        )

        # draw text
        tw, th, _, _ = gc.GetFullTextExtent(self.node.id_)
        tx = (width - tw) / 2
        ty = (height - th) / 2
        gc.DrawText(self.node.id_, tx + scrolled_pos.x, ty + scrolled_pos.y)

        selected_idx = self.canvas.selected_idx.item_copy()
        if (self.node.index in selected_idx and len(selected_idx) > 1) or (
                self.node.index in self.canvas.drag_selected_idx):
            rect = self.to_scrolled_rect(self.node.s_rect)
            rect = padded_rect(rect, theme['select_outline_padding'] * cstate.scale)

            # draw rect
            draw_rect(gc, rect, border=theme['select_box_color'],
                      border_width=theme['select_outline_width'])

    def do_left_down(self, _: Vec2):
        return True


class ReactionElement(CanvasElement):
    """CanvasElement for reactions.

    Note that if new nodes are constructed, all ReactionBezier instances that use these nodes should be
    re-constructed with the new nodes. On the other hand, if the nodes are merely modified, the
    corresponding update methods should be called.
    """
    reaction: Reaction
    _hovered_handle: Optional[BezierHandle]

    # HACK no type for canvas since otherwise there is circular dependency
    def __init__(self, reaction: Reaction, canvas, to_scrolled_fn: ToScrolledFn,
                 layer: int):
        super().__init__(to_scrolled_fn, layer)
        self.reaction = reaction
        self.canvas = canvas
        self._hovered_handle = None
        self._dragged = False

        canvas.Bind(EVT_NODE_DID_MOVE, self.node_moved)
        canvas.Bind(EVT_C_MOVE_NODE, self.c_node_moved)

    def node_moved(self, evt):
        """Handler for after a node has moved."""
        node: Node = evt.node
        # OPTIMIZE ONLY IF NECESSARY(Gary): have reverse map from node to its list of reactions.
        # and handle this event only once at someplace else
        for bz in chain(self.reaction.bezier.src_beziers, self.reaction.bezier.dest_beziers):
            if bz.node.index == node.index:
                bz.handle.position += bz.node.position - evt.old_pos
                bz.update_curve(self.reaction.bezier.centroid)
                break

    def c_node_moved(self, evt):
        """Handler for after the controller is told to move a node."""
        index = 0
        for bz in chain(self.reaction.bezier.src_beziers, self.reaction.bezier.dest_beziers):
            if bz.node.index == evt.nodei:
                ctrl = self.canvas.controller
                neti = self.canvas.net_index
                reai = self.reaction.index
                if index >= len(self.reaction.bezier.src_beziers):
                    ctrl.try_set_dest_node_handle(neti, reai, bz.node.id_, bz.handle.position)
                else:
                    ctrl.try_set_src_node_handle(neti, reai, bz.node.id_, bz.handle.position)
                break
            index += 1

    def pos_inside(self, logical_pos: Vec2) -> bool:
        return self.reaction.bezier.is_mouse_on(logical_pos) or \
            self.reaction.bezier.in_which_handle(logical_pos) is not None

    def do_mouse_enter(self, logical_pos: Vec2):
        self.do_mouse_move(logical_pos)

    def do_mouse_move(self, logical_pos: Vec2):
        if self._hovered_handle is not None:
            self._hovered_handle.mouse_hovering = False

        self._hovered_handle = self.reaction.bezier.in_which_handle(logical_pos)

        if self._hovered_handle is not None:
            self._hovered_handle.mouse_hovering = True
        return True

    def do_mouse_leave(self, logical_pos: Vec2):
        if self._hovered_handle is not None:
            self._hovered_handle.mouse_hovering = False
            self._hovered_handle = None
        return True

    def do_left_down(self, logical_pos: Vec2):
        return True

    def do_left_up(self, logical_pos: Vec2):
        if self._dragged:
            self._dragged = False
            # update every handle for convenience, even though not all might have moved

            bez = self.reaction.bezier
            ctrl = self.canvas.controller
            neti = self.canvas.net_index
            reai = self.reaction.index
            ctrl.try_start_group()
            ctrl.try_set_center_handle(neti, reai, bez.src_c_handle.position)

            for species in bez.src_beziers:
                ctrl.try_set_src_node_handle(neti, reai, species.node.id_, species.handle.position)
            for species in bez.dest_beziers:
                ctrl.try_set_dest_node_handle(neti, reai, species.node.id_, species.handle.position)
            ctrl.try_end_group()

    def do_mouse_drag(self, logical_pos: Vec2, rel_pos: Vec2):
        self._dragged = True
        if self._hovered_handle is not None:
            self._hovered_handle.do_drag(logical_pos)
            return True

    def do_paint(self, gc: wx.GraphicsContext):
        selected = self.reaction.index in self.canvas.sel_reactions_idx.item_copy()

        self.reaction.bezier.do_paint(gc, self.reaction.fill_color, self.to_scrolled_fn, selected)

        # draw centroid
        color = theme['select_box_color'] if selected else self.reaction.fill_color
        pen = wx.Pen(color)
        brush = wx.Brush(color)
        gc.SetPen(pen)
        gc.SetBrush(brush)
        radius = settings['reaction_radius'] * cstate.scale
        center = self.to_scrolled_fn(self.reaction.bezier.centroid * cstate.scale -
                                     Vec2.repeat(radius))
        gc.DrawEllipse(center.x, center.y, radius * 2, radius * 2)


class SelectBox(CanvasElement):
    """Class that represents a select box, i.e. the bounding box draw around the selected nodes.

    Supports moving and resizing operations.

    Attributes:
        CURSOR_TYPES: List of cursor types starting with that for the top-left handle and going
                      clockwise.
        nodes: List of selected nodes, as contained in this select box.
        related_elts: List of NodeElements related to each node instance; matches the node list
                      1-1.
        bounding_rect: The exact bounding rectangle (without padding).
        mode: Current input mode of the SelectBox.
    """
    CURSOR_TYPES = [wx.CURSOR_SIZENWSE, wx.CURSOR_SIZENS, wx.CURSOR_SIZENESW, wx.CURSOR_SIZEWE,
                    wx.CURSOR_SIZENWSE, wx.CURSOR_SIZENS, wx.CURSOR_SIZENESW, wx.CURSOR_SIZEWE]

    nodes: List[Node]
    related_elts: List[CanvasElement]
    bounding_rect: Rect
    _padding: float  #: padding for the bounding rectangle around the selected nodes
    _drag_rel: Vec2  #: relative position of the mouse to the bounding rect when dragging started
    _rel_positions: Optional[List[Vec2]]  #: relative positions of the nodes to the bounding rect
    _resize_handle: int  #: the node resize handle. See Canvas::_GetNodeResizeHandles for details.
    #: the minimum resize ratio for each axis, to avoid making the nodes too small
    _min_resize_ratio: Vec2
    _orig_rect: Optional[Rect]  #: the bounding rect when dragging/resizing started
    _bounds: Rect  #: the bounds that the bounding rect may not exceed

    class Mode(enum.Enum):
        IDLE = 0
        MOVING = 1
        RESIZING = 2

    def __init__(self, nodes: List[Node], bounds: Rect, controller: IController, net_index: int,
                 to_scrolled_fn: ToScrolledFn, set_cursor_fn: SetCursorFn, layer: int):
        super().__init__(to_scrolled_fn, layer)
        self.update_nodes(nodes)
        self.set_cursor_fn = set_cursor_fn
        self.controller = controller
        self.net_index = net_index
        self._mode = SelectBox.Mode.IDLE

        self._drag_rel = Vec2()
        self._rel_positions = None
        self._orig_rect = None
        self._resize_handle = -1
        self._min_resize_ratio = Vec2()
        self._hovered_part = -2

        self._bounds = bounds

    @property
    def mode(self):
        return self._mode

    def update_nodes(self, nodes: List[Node]):
        self.nodes = nodes
        if len(nodes) > 0:
            self._padding = theme['select_box_padding'] if len(nodes) > 1 else \
                theme['select_outline_padding']
            rects = [n.rect for n in nodes]
            self.bounding_rect = get_bounding_rect(rects)

    def outline_rect(self) -> Rect:
        """Helper that returns the scaled, padded bounding rectangle."""
        return padded_rect(self.bounding_rect * cstate.scale, self._padding)

    def _resize_handle_rects(self):
        """Helper that computes the scaled positions and sizes of the resize handles.

        Returns:
            A list of (pos, size) tuples representing the resize handle
            rectangles. They are ordered such that the top-left handle is the first element, and
            all other handles follow in clockwise fashion.
        """
        outline_rect = self.outline_rect()
        pos, size = outline_rect.as_tuple()
        centers = [pos, pos + Vec2(size.x / 2, 0),
                   pos + Vec2(size.x, 0), pos + Vec2(size.x, size.y / 2),
                   pos + size, pos + Vec2(size.x / 2, size.y),
                   pos + Vec2(0, size.y), pos + Vec2(0, size.y / 2)]
        side = theme['select_handle_length']
        return [Rect(c - Vec2.repeat(side/2), Vec2.repeat(side)) for c in centers]

    def _pos_inside_part(self, logical_pos: Vec2) -> int:
        """Helper for determining if logical_pos is within which, if any, part of this widget.

        Returns:
            The handle index (0-3) if pos is within a handle, -1 if pos is not within a handle
            but within the bounding rectangle, or -2 if pos is outside.
        """
        if len(self.nodes) == 0:
            return -2

        rects = self._resize_handle_rects()
        for i, rect in enumerate(rects):
            if within_rect(logical_pos, rect):
                return i

        if within_rect(logical_pos, self.bounding_rect * cstate.scale):
            return -1
        else:
            return -2

    def pos_inside(self, logical_pos: Vec2):
        return self._pos_inside_part(logical_pos) != -2

    def do_mouse_enter(self, logical_pos: Vec2):
        self.do_mouse_move(logical_pos)

    def do_mouse_move(self, logical_pos: Vec2):
        self._hovered_part = self._pos_inside_part(logical_pos)
        return True

    def do_mouse_leave(self, logical_pos: Vec2):
        self._hovered_part = -2
        return True

    def do_paint(self, gc: wx.GraphicsContext):
        if len(self.nodes) > 0:
            outline_width = theme['select_outline_width'] if len(self.nodes) == 1 else \
                theme['select_outline_width']
            pos, size = self.outline_rect().as_tuple()
            adj_pos = Vec2(self.to_scrolled_fn(pos))

            # draw main outline
            draw_rect(gc, Rect(adj_pos, size), border=theme['select_box_color'],
                      border_width=outline_width)

            for handle_rect in self._resize_handle_rects():
                # convert to device position for drawing
                rpos, rsize = handle_rect.as_tuple()
                rpos = Vec2(self.to_scrolled_fn(rpos))
                draw_rect(gc, Rect(rpos, rsize), fill=theme['select_box_color'])

            if self._hovered_part >= 0:
                cursor = SelectBox.CURSOR_TYPES[self._hovered_part]
                self.set_cursor_fn(wx.Cursor(cursor))
                pass
            elif self._hovered_part == -1:
                self.set_cursor_fn(wx.Cursor(wx.CURSOR_ARROW))
            else:
                self.set_cursor_fn(wx.Cursor(wx.CURSOR_ARROW))

    def do_left_down(self, logical_pos: Vec2):
        if len(self.nodes) == 0:
            return False

        # if multi-selecting and clicked on a node/reaction, then the user must mean to de-select
        # that element. In this exceptional case we return False so that canvas can continue the
        # pos_inside loop and find the node/reaction in question later.
        if cstate.multi_select:
            for elt in self.related_elts:
                if elt.pos_inside(logical_pos):
                    return False

        handle = self._hovered_part
        assert self._mode == SelectBox.Mode.IDLE
        if handle >= 0:
            self._mode = SelectBox.Mode.RESIZING
            self._resize_handle = handle
            min_width = min(n.size.x for n in self.nodes)
            min_height = min(n.size.y for n in self.nodes)
            self._min_resize_ratio = Vec2(theme['min_node_width'] / min_width,
                                          theme['min_node_height'] / min_height)
            self._orig_rect = self.outline_rect()
            self._orig_positions = [n.s_position - self._orig_rect.position - Vec2.repeat(self._padding)
                                    for n in self.nodes]
            self._orig_sizes = [n.s_size for n in self.nodes]
            return True
        elif handle == -1:
            self._mode = SelectBox.Mode.MOVING
            self._rel_positions = [n.s_position - logical_pos for n in self.nodes]
            self._drag_rel = self.bounding_rect.position * cstate.scale - logical_pos
            return True

        return False

    def do_left_up(self, logical_pos: Vec2):
        assert len(self.nodes) != 0
        if self._mode == SelectBox.Mode.MOVING:
            self.controller.try_start_group()
            for node in self.nodes:
                self.controller.try_move_node(self.net_index, node.index, node.position)
            self.controller.try_end_group()
        else:
            assert self._mode == SelectBox.Mode.RESIZING
            self.controller.try_start_group()
            for node in self.nodes:
                self.controller.try_move_node(self.net_index, node.index, node.position)
                self.controller.try_set_node_size(self.net_index, node.index, node.size)
            self.controller.try_end_group()
        self._mode = SelectBox.Mode.IDLE

    def do_mouse_drag(self, logical_pos: Vec2, rel_pos: Vec2) -> bool:
        assert self._mode != SelectBox.Mode.IDLE
        if self._mode == SelectBox.Mode.RESIZING:
            self._resize(logical_pos)
        else:
            self._move(logical_pos)
        return True

    def _resize(self, pos: Vec2):
        """Helper that performs resize on the bounding box, given the logical mouse position."""
        # STEP 1, get new rect vertices
        # see class comment for resize handle format. For side-handles, get the vertex in the
        # counter-clockwise direction
        dragged_idx = self._resize_handle // 2
        fixed_idx = int((dragged_idx + 2) % 4)  # get the vertex opposite dragged idx as fixed_idx
        orig_dragged_point = self._orig_rect.nth_vertex(dragged_idx)
        cur_dragged_point = self.outline_rect().nth_vertex(dragged_idx)
        fixed_point = self._orig_rect.nth_vertex(fixed_idx)

        target_point = pos

        # if a side-handle, then only resize one axis
        if self._resize_handle % 2 == 1:
            if self._resize_handle % 4 == 1:
                # vertical resize; keep x the same
                target_point.x = orig_dragged_point.x
            else:
                assert self._resize_handle % 4 == 3
                target_point.y = orig_dragged_point.y

        # clamp target point
        target_point = clamp_point(target_point, self._bounds * cstate.scale)

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
            node.position = (br_pos + orig_pos.elem_mul(size_ratio)) / cstate.scale + pad_off
            node.size = orig_size.elem_mul(size_ratio) / cstate.scale

        # STEP 5 apply new bounding_rect position and size
        self.bounding_rect.position = br_pos / cstate.scale + pad_off
        self.bounding_rect.size = target_size / cstate.scale

    def _move(self, pos: Vec2):
        """Helper that performs resize on the bounding box, given the logical mouse position."""
        # campute tentative new positions. May need to clamp it.
        new_positions = [pos + rp for rp in self._rel_positions]
        min_x = min(p.x for p in new_positions)
        min_y = min(p.y for p in new_positions)
        max_x = max(p.x + n.s_size.x for p, n in zip(new_positions, self.nodes))
        max_y = max(p.y + n.s_size.y for p, n in zip(new_positions, self.nodes))
        offset = Vec2(0, 0)

        s_bounds = self._bounds * cstate.scale
        lim_topleft = s_bounds.position
        lim_botright = s_bounds.position + self._bounds.size

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

        self.bounding_rect.position = (pos + offset + self._drag_rel) / cstate.scale
        for node, np in zip(self.nodes, new_positions):
            node.position = (np + offset) / cstate.scale
