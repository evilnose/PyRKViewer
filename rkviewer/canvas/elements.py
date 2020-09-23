from __future__ import annotations
# pylint: disable=maybe-no-member
from abc import abstractmethod
import bisect
import enum
from functools import partial
from itertools import chain
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union, cast

import wx

from ..config import settings, theme
from ..events import (
    CanvasEvent, DidDragResizeNodesEvent,
    DidMoveNodesEvent, bind_handler,
    post_event, unbind_handler,
)
from ..mvc import IController
from ..utils import even_round, gchain, int_round
from .data import Compartment, HandleData, Node, Reaction, ReactionBezier, SpeciesBezier, compute_centroid
from .geometry import (
    Rect,
    Vec2,
    clamp_point,
    get_bounding_rect,
    padded_rect,
    pt_in_circle,
    within_rect,
)
from .state import cstate
from .utils import draw_rect


SetCursorFn = Callable[[wx.Cursor], None]


class CanvasElement:
    """Base class for an element positioned on the canvas.

    Attributes:
        layer: The layer number of this element.
    """
    layers: List[int]
    enabled: bool
    destroyed: bool

    def __init__(self, layers: Union[int, List[int]]):
        if isinstance(layers, int):
            layers = [layers]
        self.layers = layers
        self.enabled = True
        self.destroyed = False

    def set_layers(self, layers: Union[int, List[int]]):
        if isinstance(layers, int):
            self.layers = [layers]

    def destroy(self):
        """Destroy this element; override this for specific implementations."""
        self.destroyed = True

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


class NodeElement(CanvasElement):
    """CanvasElement for nodes."""
    node: Node
    canvas: Any

    # HACK no type specified for canvas since otherwise there would be circular dependency
    def __init__(self, node: Node, canvas, layer: int):
        super().__init__(layer)
        self.node = node
        self.canvas = canvas
        self.gfont = None  # In the future
        self.font_scale = 1

    def pos_inside(self, logical_pos: Vec2) -> bool:
        return within_rect(logical_pos, self.node.s_rect)

    def do_paint(self, gc: wx.GraphicsContext):
        if self.gfont is None or self.font_scale != cstate.scale:
            self.font_scale = cstate.scale
            font = wx.Font(wx.FontInfo(10 * cstate.scale))
            self.gfont = gc.CreateFont(font, wx.BLACK)
        gc.SetFont(self.gfont)

        s_aligned_rect = self.node.s_rect.aligned()
        aligned_border_width = max(even_round(self.node.border_width * cstate.scale), 2)
        width, height = s_aligned_rect.size
        draw_rect(
            gc,
            s_aligned_rect,
            fill=self.node.fill_color,
            border=self.node.border_color,
            border_width=aligned_border_width,
        )

        # draw text
        tw, th, _, _ = gc.GetFullTextExtent(self.node.id_)  # optimize by caching?
        tx = (width - tw) / 2
        ty = (height - th) / 2
        gc.DrawText(self.node.id_, self.node.s_position.x + tx, self.node.s_position.y + ty)

    def do_left_down(self, _: Vec2):
        return True


class BezierHandle(CanvasElement):
    """Class that keeps track of a Bezier control handle tip.

    Attributes:
        HANDLE_RADIUS: radius of the control handle.
        data: The associated HandleData>
        on_moved: The function called when the handle is moved.
        on_dropped: The function called when the handle is dropped (i.e. mouse up).
        reaction: The associated Reaction.
    """
    HANDLE_RADIUS = 5  # Radius of the control handle

    data: HandleData
    on_moved: Callable[[Vec2], None]
    on_dropped: Callable[[Vec2], None]
    reaction: Reaction

    def __init__(self, data: HandleData, layer: int,
                 on_moved: Callable[[Vec2], None],
                 on_dropped: Callable[[Vec2], None], reaction: Reaction):
        super().__init__(layer)
        self.data = data
        self.on_moved = on_moved
        self.on_dropped = on_dropped
        self.reaction = reaction
        self.hovering = False
        self.enabled = False

    def pos_inside(self, logical_pos: Vec2):
        return pt_in_circle(logical_pos, BezierHandle.HANDLE_RADIUS, self.data.tip * cstate.scale)

    def do_paint(self, gc: wx.GraphicsContext):
        """Paint the handle as given by its base and tip positions, highlighting it if hovering."""
        assert self.data.base is not None
        c = theme['highlighted_handle_color'] if self.hovering else theme['handle_color']
        brush = wx.Brush(c)
        pen = gc.CreatePen(wx.GraphicsPenInfo(c))

        sbase = self.data.base * cstate.scale
        stip = self.data.tip * cstate.scale

        gc.SetPen(pen)

        # Draw handle lines
        gc.StrokeLine(*sbase, *stip)

        # Draw handle circles
        gc.SetBrush(brush)
        gc.DrawEllipse(stip.x - BezierHandle.HANDLE_RADIUS,
                       stip.y - BezierHandle.HANDLE_RADIUS,
                       2 * BezierHandle.HANDLE_RADIUS, 2 * BezierHandle.HANDLE_RADIUS)

    def do_mouse_enter(self, logical_pos: Vec2) -> bool:
        self.hovering = True
        return True

    def do_mouse_leave(self, logical_pos: Vec2) -> bool:
        self.hovering = False
        return True

    def do_left_down(self, logical_pos: Vec2) -> bool:
        return True

    def do_mouse_drag(self, logical_pos: Vec2, rel_pos: Vec2) -> bool:
        self.data.tip += rel_pos / cstate.scale
        self.on_moved(self.data.tip)
        return True

    def do_left_up(self, logical_pos: Vec2):
        self.on_dropped(self.data.tip)
        return True


# Uniquely identifies nodes in a reaction: (regular node index; whether the node is a reactant)
RIndex = Tuple[int, bool]


class ReactionElement(CanvasElement):
    """CanvasElement for reactions.

    Note that if new nodes are constructed, all ReactionBezier instances that use these nodes should
    be re-constructed with the new nodes. On the other hand, if the nodes are merely modified, the
    corresponding update methods should be called.
    """
    reaction: Reaction
    index_to_bz: Dict[RIndex, SpeciesBezier]
    moved_handler_id: int
    #: Set of indices of the nodes that have been moved, but not committed.
    _dirty_node_indices: Set[int]
    #: Works in tandem with _dirty_indices. True if all nodes of the reaction are being moved.
    _moving_all: bool
    _selected: bool

    # HACK no type for canvas since otherwise there is circular dependency
    def __init__(self, reaction: Reaction, bezier: ReactionBezier, canvas, layer: int, handle_layer: int):
        super().__init__(layer)
        self.reaction = reaction
        self.bezier = bezier
        self.moved_handler_id = bind_handler(DidMoveNodesEvent, self.nodes_moved)
        # i is 0 for source Beziers, but 1 for dest Beziers. "not" it to get the correct bool.
        self.index_to_bz = {(bz.node_idx, not gi): bz
                            for gi, bz in gchain(bezier.src_beziers,
                                                 bezier.dest_beziers)}
        self.canvas = canvas
        self._hovered_handle = None
        self._dirty_indices = set()
        self._moving_all = False
        self.beziers = list()
        self._selected = False

        neti = canvas.net_index
        reai = reaction.index
        ctrl = canvas.controller
        # create elements for species
        for gi, sb in gchain(bezier.src_beziers, bezier.dest_beziers):
            dropped_func = self.make_drop_handle_func(ctrl, neti, reai, sb.node_idx, not gi)
            el = BezierHandle(sb.handle, handle_layer,
                              bezier.make_handle_moved_func(sb), dropped_func, reaction)
            self.beziers.append(el)

        def centroid_handle_dropped(p: Vec2):
            ctrl.start_group()
            ctrl.set_center_handle(neti, reai, reaction.src_c_handle.tip)
            ctrl.end_group()

        self.beziers.append(BezierHandle(reaction.src_c_handle, handle_layer,
                                         lambda _: bezier.src_handle_moved(),
                                         centroid_handle_dropped, reaction))
        self.beziers.append(BezierHandle(reaction.dest_c_handle, handle_layer,
                                         lambda _: bezier.dest_handle_moved(),
                                         centroid_handle_dropped, reaction))

    def make_drop_handle_func(self, ctrl: IController, neti: int, reai: int, nodei: int,
                              is_source: bool):
        if is_source:
            return lambda p: ctrl.set_src_node_handle(neti, reai, nodei, p)
        else:
            return lambda p: ctrl.set_dest_node_handle(neti, reai, nodei, p)

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, val: bool):
        # Enable/disable Handles based on whether the curve is selected
        self._selected = val
        for bz in self.beziers:
            bz.enabled = val

    def nodes_moved(self, evt: CanvasEvent):
        """Handler for after a node has moved."""
        # If already moving (i.e. self._dirty_indices is not empty), then skip forward
        c_evt = cast(DidMoveNodesEvent, evt)
        nodes = c_evt.nodes
        offset = c_evt.offset
        rects = [self.canvas.node_idx_map[idx].rect for idx in chain(
            self.reaction.sources, self.reaction.targets)]
        self.bezier.nodes_moved(rects)
        if len(self._dirty_indices) == 0:
            self._dirty_indices = {n.index for n in nodes}
            my_indices = {idx for idx in chain(self.reaction.sources, self.reaction.targets)}
            self._moving_all = my_indices <= self._dirty_indices

        for node in nodes:
            for in_src in [True, False]:
                if (node.index, in_src) in self.index_to_bz:
                    bz = self.index_to_bz[(node.index, in_src)]
                    bz.handle.tip += offset
                    bz.update_curve(self.bezier.centroid)

        if self._moving_all:
            self.reaction.src_c_handle.tip += offset
            self.bezier.src_handle_moved()

    def commit_node_pos(self):
        """Handler for after the controller is told to move a node."""
        ctrl = self.canvas.controller
        neti = self.canvas.net_index
        reai = self.reaction.index
        for bz in self.bezier.src_beziers:
            if bz.node_idx in self._dirty_indices:
                ctrl.set_src_node_handle(neti, reai, bz.node_idx, bz.handle.tip)

        for bz in self.bezier.dest_beziers:
            if bz.node_idx in self._dirty_indices:
                ctrl.set_dest_node_handle(neti, reai, bz.node_idx, bz.handle.tip)

        if self._moving_all:
            ctrl.set_center_handle(neti, reai, self.reaction.src_c_handle.tip)
        self._dirty_indices = set()

    def destroy(self):
        unbind_handler(self.moved_handler_id)
        super().destroy()

    def pos_inside(self, logical_pos: Vec2) -> bool:
        return self.bezier.is_mouse_on(logical_pos)

    def do_mouse_enter(self, logical_pos: Vec2):
        self.do_mouse_move(logical_pos)

    def do_left_down(self, logical_pos: Vec2) -> bool:
        return True  # Return True so that this can be selected

    def do_paint(self, gc: wx.GraphicsContext):
        self.bezier.do_paint(gc, self.reaction.fill_color, self.selected)

        # draw centroid
        color = theme['handle_color'] if self.selected else self.reaction.fill_color
        pen = wx.Pen(color)
        brush = wx.Brush(color)
        gc.SetPen(pen)
        gc.SetBrush(brush)
        radius = settings['reaction_radius'] * cstate.scale
        center = self.bezier.centroid * cstate.scale - Vec2.repeat(radius)
        gc.DrawEllipse(center.x, center.y, radius * 2, radius * 2)


class CompartmentElt(CanvasElement):
    def __init__(self, compartment: Compartment, major_layer: int, minor_layer: int):
        super().__init__([major_layer, minor_layer])
        self.compartment = compartment

    def pos_inside(self, logical_pos: Vec2) -> bool:
        return within_rect(logical_pos, self.compartment.rect)

    def do_left_down(self, logical_pos: Vec2) -> bool:
        return True

    def do_paint(self, gc: wx.GraphicsContext):
        rect = Rect(self.compartment.position, self.compartment.size) * cstate.scale
        draw_rect(gc, rect, border=self.compartment.border,
                  border_width=self.compartment.border_width, fill=self.compartment.fill)


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
    HANDLE_MULT = [Vec2(), Vec2(1/2, 0), Vec2(1, 0), Vec2(1, 1/2),
                   Vec2(1, 1), Vec2(1/2, 1), Vec2(0, 1), Vec2(0, 1/2)]

    nodes: List[Node]
    related_elts: List[CanvasElement]
    bounding_rect: Rect
    _padding: float  #: padding for the bounding rectangle around the selected nodes
    _drag_rel: Vec2  #: relative position of the mouse to the bounding rect when dragging started
    _did_move: bool  #: whether the node was drag-moved between left_down and left_up.
    _rel_positions: Optional[List[Vec2]]  #: relative positions of the nodes to the bounding rect
    _resize_handle: int  #: the node resize handle.
    #: the minimum resize ratio for each axis, to avoid making the nodes too small
    _min_resize_ratio: Vec2
    _orig_rect: Optional[Rect]  #: the bounding rect when dragging/resizing started
    _bounds: Rect  #: the bounds that the bounding rect may not exceed

    class Mode(enum.Enum):
        IDLE = 0
        MOVING = 1
        RESIZING = 2

    def __init__(self, canvas, nodes: List[Node], compartments: List[Compartment], bounds: Rect,
                 controller: IController, net_index: int, set_cursor_fn: SetCursorFn, layer: int):
        super().__init__(layer)
        self.canvas = canvas
        self.update(nodes, compartments)
        self.set_cursor_fn = set_cursor_fn
        self.controller = controller
        self.net_index = net_index
        self._mode = SelectBox.Mode.IDLE

        self._drag_rel = Vec2()
        self._did_move = False
        self._rel_positions = None
        self._orig_rect = None
        self._resize_handle = -1
        self._min_resize_ratio = Vec2()
        self._hovered_part = -2

        self._bounds = bounds

    @property
    def mode(self):
        return self._mode

    def update(self, nodes: List[Node], compartments: List[Compartment]):
        self.nodes = nodes
        self.compartments = compartments

        if len(nodes) + len(compartments) > 0:
            if len(nodes) == 1 and len(compartments) == 0:
                # If only one node is selected, reduce padding
                self._padding = theme['select_outline_padding']
            else:
                self._padding = theme['select_box_padding']
            # Align bounding box if only one node is selected, see NodeElement::do_paint for
            # explanations. Note that self._padding should be an integer
            self._padding = int_round(self._padding)
            self.bounding_rect = get_bounding_rect(
                [n.rect for n in nodes] + [c.rect for c in compartments])

        # TODO document
        self.assoc_comps = {self.canvas.node2comp[n.index] for n in nodes}

    def outline_rect(self) -> Rect:
        """Helper that returns the scaled, padded bounding rectangle."""
        return padded_rect((self.bounding_rect * cstate.scale).aligned(), self._padding)

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
        centers = [pos + size.elem_mul(m) for m in SelectBox.HANDLE_MULT]
        side = theme['select_handle_length']
        return [Rect(c - Vec2.repeat(side/2), Vec2.repeat(side)) for c in centers]

    def _resize_handle_pos(self, n: int):
        pos, size = self.outline_rect().as_tuple()
        assert n >= 0 and n < 8
        return pos + size.elem_mul(SelectBox.HANDLE_MULT[n])

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
        if len(self.nodes) + len(self.compartments) > 0:
            outline_width = max(even_round(theme['select_outline_width']), 2)
            pos, size = self.outline_rect().as_tuple()

            # draw main outline
            draw_rect(gc, Rect(pos, size), border=theme['handle_color'],
                      border_width=outline_width)

            for handle_rect in self._resize_handle_rects():
                # convert to device position for drawing
                draw_rect(gc, handle_rect, fill=theme['handle_color'])

            if self._hovered_part >= 0:
                cursor = SelectBox.CURSOR_TYPES[self._hovered_part]
                self.set_cursor_fn(wx.Cursor(cursor))
                pass
            elif self._hovered_part == -1:
                # HACK re-set input_mode with the same value to make canvas update the cursor
                # See issue #9 for details
                cstate.input_mode = cstate.input_mode
            else:
                cstate.input_mode = cstate.input_mode

    def do_left_down(self, logical_pos: Vec2):
        if len(self.nodes) + len(self.compartments) == 0:
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
            self._min_resize_ratio = Vec2(settings['min_node_width'] / min_width,
                                          settings['min_node_height'] / min_height)
            self._orig_rect = self.outline_rect()
            self._orig_positions = [n.s_position - self._orig_rect.position - Vec2.repeat(self._padding)
                                    for n in self.nodes]
            self._orig_sizes = [n.s_size for n in self.nodes]
            self._resize_handle_offset = self._resize_handle_pos(handle) - logical_pos
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
            if self._did_move:
                self._did_move = False
                self.controller.start_group()

                # TODO write out logic for moving/resizing multiple selected nodes/compartments
                for node in self.nodes:
                    self.controller.move_node(self.net_index, node.index, node.position)
                    # TODO change this to controller code once possible
                bounding_rect = get_bounding_rect([n.rect for n in self.nodes])
                for comp in reversed(self.compartments):
                    if comp.rect.contains(bounding_rect):
                        pass  # TODO Here
                self.controller.end_group()
        elif self._mode == SelectBox.Mode.RESIZING:
            assert not self._did_move
            self.controller.start_group()
            for node in self.nodes:
                self.controller.move_node(self.net_index, node.index, node.position)
                self.controller.set_node_size(self.net_index, node.index, node.size)
            self.controller.end_group()
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

        target_point = pos + self._resize_handle_offset

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
        # incremental ratio for the event
        inc_ratio = orig_size.elem_mul(size_ratio / cstate.scale).elem_div(self.nodes[0].size)
        for node, orig_pos, orig_size in zip(self.nodes, self._orig_positions, self._orig_sizes):
            assert orig_pos.x >= -1e-6 and orig_pos.y >= -1e-6
            node.position = (br_pos + orig_pos.elem_mul(size_ratio)) / cstate.scale + pad_off
            node.size = orig_size.elem_mul(size_ratio) / cstate.scale
            assert node.size == node.s_size and node.size == node.rect.size

        # STEP 5 apply new bounding_rect position and size
        self.bounding_rect.position = br_pos / cstate.scale + pad_off
        self.bounding_rect.size = target_size / cstate.scale

        # STEP 6 post event
        post_event(DidDragResizeNodesEvent(nodes=self.nodes, ratio=inc_ratio))

    def _move(self, pos: Vec2):
        """Helper that performs resize on the bounding box, given the logical mouse position."""
        # campute tentative new positions. May need to clamp it.
        self._did_move = True
        new_positions = [pos + rp for rp in self._rel_positions]
        min_x = min(p.x for p in new_positions)
        min_y = min(p.y for p in new_positions)
        max_x = max(p.x + n.s_size.x for p, n in zip(new_positions, self.nodes))
        max_y = max(p.y + n.s_size.y for p, n in zip(new_positions, self.nodes))
        offset = Vec2(0, 0)

        s_bounds = self._bounds * cstate.scale
        lim_topleft = s_bounds.position
        lim_botright = s_bounds.position + s_bounds.size

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
        pos_offset = (new_positions[0] + offset) / cstate.scale - self.nodes[0].position
        for node, np in zip(self.nodes, new_positions):
            node.position = (np + offset) / cstate.scale
        post_event(DidMoveNodesEvent(self.nodes, pos_offset, dragged=True))
