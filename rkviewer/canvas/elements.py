from __future__ import annotations
# pylint: disable=maybe-no-member
from abc import abstractmethod
import enum
from functools import partial
from itertools import chain
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Set, Tuple, Union, cast
from copy import copy

import wx

from ..config import get_setting, get_theme
from ..events import (
    CanvasEvent, DidChangeCompartmentOfNodesEvent, DidCommitDragEvent, DidMoveBezierHandleEvent, DidMoveReactionCenterEvent, DidResizeCompartmentsEvent, DidResizeNodesEvent, DidMoveCompartmentsEvent,
    DidMoveNodesEvent, bind_handler,
    post_event, unbind_handler,
)
from ..mvc import IController
from ..utils import change_opacity, even_round, gchain, int_round
from .data import Compartment, HandleData, Node, Reaction, ReactionBezier, RectData, SpeciesBezier
from .geometry import (
    Rect,
    Vec2,
    clamp_point, clamp_rect_pos,
    get_bounding_rect,
    padded_rect,
    pt_in_circle,
    pt_in_rect,
)
from .state import cstate
from .utils import draw_rect


SetCursorFn = Callable[[wx.Cursor], None]
Layer = Union[int, Tuple[int, ...]]


def layer_above(layer: Layer, count: int = 1) -> Layer:
    """
    Return the next layer above this layer, without increasing the length of the layer list.

    count is optionally the layer number increment.
    """
    if count < 1:
        raise ValueError('Layer count must be at least 1!')
    if isinstance(layer, int):
        return layer + count
    else:
        last = len(layer) - 1
        return layer[0:last] + (layer[last] + count,)


class CanvasElement:
    """Base class for an element positioned on the canvas.

    Attributes:
        layers: The layer(s) number of this element.
        enabled: Whether the element is enabled.
        destroyed: Whether the object was destroyed (if this is True then you shouldn't use this)
    """
    layers: Layer
    enabled: bool
    destroyed: bool

    def __init__(self, layers: Layer):
        if isinstance(layers, int):
            layers = (layers,)
        self.layers = layers
        self.enabled = True
        self.destroyed = False

    def set_layers(self, layers: Layer):
        if isinstance(layers, int):
            layers = (layers,)
        self.layers = layers

    def destroy(self):
        """Destroy this element; override this for specific implementations."""
        self.destroyed = True

    def pos_inside(self, logical_pos: Vec2) -> bool:
        """Returns whether logical_pos is inside the diplayed shape of this element."""
        return False

    @abstractmethod
    def on_paint(self, gc: wx.GraphicsContext):
        """Paint the shape onto the given GraphicsContext.
        
        This draws onto the scrolled canvas, i.e. the position of the drawn item will respond to
        scrolling, so you don't need to account for that.
        """
        pass

    def on_mouse_enter(self, logical_pos: Vec2) -> bool:
        """Handler for when the mouse has entered the shape."""
        return False

    def on_mouse_leave(self, logical_pos: Vec2) -> bool:
        """Handler for when the mouse has exited the shape"""
        return False

    def on_mouse_move(self, logical_pos: Vec2) -> bool:
        """Handler for when the mouse moves inside the shape, with the left mouse button up."""
        return False

    def on_mouse_drag(self, logical_pos: Vec2, rel_pos: Vec2) -> bool:
        """Handler for when the mouse drags inside the shape, with the left mouse button down."""
        return False

    def on_left_down(self, logical_pos: Vec2) -> bool:
        """Handler for when the mouse left button is pressed down inside the shape."""
        return False

    def on_left_up(self, logical_pos: Vec2) -> bool:
        """Handler for when the mouse left button is springs up inside the shape."""
        return False


class NodeElement(CanvasElement):
    """CanvasElement for nodes."""
    node: Node
    canvas: Any

    # HACK no type specified for canvas since otherwise there would be circular dependency
    def __init__(self, node: Node, canvas, layers: Layer):
        super().__init__(layers)
        self.node = node
        self.canvas = canvas
        self.gfont = None  # In the future
        self.font_scale = 1

    def pos_inside(self, logical_pos: Vec2) -> bool:
        return pt_in_rect(logical_pos, self.node.s_rect)

    def on_paint(self, gc: wx.GraphicsContext):
        if self.gfont is None or self.font_scale != cstate.scale:
            self.font_scale = cstate.scale
            font = wx.Font(wx.FontInfo(10 * cstate.scale))
            self.gfont = gc.CreateFont(font, wx.BLACK)
        gc.SetFont(self.gfont)

        boundaryFactor = 1
        if not self.node.floatingNode:
           boundaryFactor = 2  # Store this in a theme? 

        s_aligned_rect = self.node.s_rect.aligned()
        aligned_border_width = max(even_round(
            self.node.border_width * boundaryFactor * cstate.scale), 2)
        width, height = s_aligned_rect.size
        draw_rect(
            gc,
            s_aligned_rect,
            fill=self.node.fill_color,
            border=self.node.border_color,
            border_width=aligned_border_width,
            corner_radius=get_theme('node_corner_radius')
        )

        # draw text
        tw, th, _, _ = gc.GetFullTextExtent(
            self.node.id)  # optimize by caching?
        tx = (width - tw) / 2
        ty = (height - th) / 2
        gc.DrawText(self.node.id, self.node.s_position.x +
                    tx, self.node.s_position.y + ty)

    def on_left_down(self, _: Vec2):
        return True


class BezierHandle(CanvasElement):
    """Class that keeps track of a Bezier control handle tip.

    Attributes:
        HANDLE_RADIUS: radius of the control handle.
        data: The associated HandleData>
        on_moved: The function called when the handle is moved.
        on_dropped: The function called when the handle is dropped (i.e. mouse up).
        reaction: The associated Reaction.
        twin: The twin BezierHandle; used only for the center handles.
        node_idx: The index of the node associated with this handle. -1 if this is a source
                  centroid handle, and -2 if this is a target centroid handle.
    """
    HANDLE_RADIUS = 5  # Radius of the control handle

    data: HandleData
    on_moved: Callable[[Vec2], None]
    on_dropped: Callable[[Vec2], None]
    reaction: Reaction
    twin = Any
    node_idx: int

    def __init__(self, data: HandleData, layer: Layer, on_moved: Callable[[Vec2], None],
                 on_dropped: Callable[[Vec2], None], reaction: Reaction, node_idx: int):
        super().__init__(layer)
        self.data = data
        self.on_moved = on_moved
        self.on_dropped = on_dropped
        self.reaction = reaction
        self.hovering = False
        self.enabled = False
        self.twin = None
        self.node_idx = node_idx

    def pos_inside(self, logical_pos: Vec2):
        return pt_in_circle(logical_pos, BezierHandle.HANDLE_RADIUS, self.data.tip * cstate.scale)
    
    def on_paint(self, gc: wx.GraphicsContext):
        """Paint the handle as given by its base and tip positions, highlighting it if hovering."""
        assert self.data.base is not None
        if self.reaction.bezierCurves:
            c = get_theme('highlighted_handle_color') if self.hovering else get_theme('handle_color')
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

    def on_mouse_enter(self, logical_pos: Vec2) -> bool:
        self.hovering = True
        if self.twin:
            self.twin.hovering = True
        return True

    def on_mouse_leave(self, logical_pos: Vec2) -> bool:
        self.hovering = False
        if self.twin:
            self.twin.hovering = False
        return True

    def on_left_down(self, logical_pos: Vec2) -> bool:
        return True

    def on_mouse_drag(self, logical_pos: Vec2, rel_pos: Vec2) -> bool:
        self.data.tip += rel_pos / cstate.scale
        self.on_moved(self.data.tip)
        neti = 0
        post_event(DidMoveBezierHandleEvent(neti, self.reaction.index,
                                            self.node_idx, by_user=True, direct=True))

        return True

    def on_left_up(self, logical_pos: Vec2):
        self.on_dropped(self.data.tip)
        return True


class ReactionCenter(CanvasElement):
    parent: ReactionElement
    _moved: bool

    def __init__(self, parent: ReactionElement, layers: Layer):
        super().__init__(layers)
        self.parent = parent
        self._moved = False
        self.hovering = False
    
    def on_paint(self, gc: wx.GraphicsContext):
        # draw centroid
        color = self.parent.reaction.fill_color
        if self.parent.selected:
            if self.hovering:
                color = get_theme('highlighted_handle_color')
            else:
                color = get_theme('handle_color')
        pen = wx.Pen(color)
        brush = wx.Brush(color)
        gc.SetPen(pen)
        gc.SetBrush(brush)
        radius = get_theme('reaction_radius')
        center = self.parent.bezier.real_center * cstate.scale - Vec2.repeat(radius)
        gc.DrawEllipse(center.x, center.y, radius * 2, radius * 2)

    def on_left_down(self, logical_pos: Vec2) -> bool:
        # If not selected, then nothing is done to prevent accidental dragging
        return True

    def on_mouse_drag(self, logical_pos: Vec2, rel_pos: Vec2) -> bool:
        offset = rel_pos / cstate.scale
        reaction = self.parent.reaction
        reaction.center_pos = self.parent.bezier.real_center + offset
        self.parent.bezier.center_moved(offset)
        self._moved = True
        net_index = 0
        post_event(DidMoveReactionCenterEvent(net_index, reaction.index, offset, True))
        return True

    def on_left_up(self, logical_pos: Vec2) -> bool:
        ctrl = self.parent.controller
        neti = self.parent.canvas.net_index
        reai = self.parent.reaction.index
        ctrl.start_group()
        ctrl.set_reaction_center(neti, reai, self.parent.reaction.center_pos)
        ctrl.set_center_handle(neti, reai, self.parent.reaction.src_c_handle.tip)
        post_event(DidCommitDragEvent())
        ctrl.end_group()
        self._moved = False
        return True

    def pos_inside(self, logical_pos: Vec2) -> bool:
        # TODO works witih zoom?
        radius = get_theme('reaction_radius')
        return pt_in_circle(self.parent.bezier.real_center * cstate.scale, radius, logical_pos)

    def on_mouse_enter(self, logical_pos: Vec2) -> bool:
        self.hovering = True
        return True

    def on_mouse_leave(self, logical_pos: Vec2) -> bool:
        self.hovering = False
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
    center_el: ReactionCenter
    index_to_bz: Dict[RIndex, SpeciesBezier]
    bezier: ReactionBezier
    bhandles: List[BezierHandle]
    moved_handler_id: int
    #: Set of indices of the nodes that have been moved, but not committed.
    _dirty_node_indices: Set[int]
    #: Works in tandem with _dirty_indices. True if all nodes of the reaction are being moved.
    _moving_all: bool
    _selected: bool
    canvas: Any  # avoid circular dependency
    controller: IController

    # HACK no type for canvas since otherwise there is circular dependency
    def __init__(self, reaction: Reaction, bezier: ReactionBezier, canvas, layers: Layer, handle_layer: Layer):
        super().__init__(layers)
        self.reaction = reaction
        self.bezier = bezier
        self.moved_handler_id = bind_handler(DidMoveNodesEvent, self.nodes_moved)
        # i is 0 for source Beziers, but 1 for dest Beziers. "not" it to get the correct bool.
        self.index_to_bz = {(bz.node_idx, not gi): bz
                            for gi, bz in gchain(bezier.src_beziers,
                                                 bezier.dest_beziers)}
        self.canvas = canvas
        self.controller = canvas.controller
        self._hovered_handle = None
        self._dirty_indices = set()
        self._moving_all = False
        self.bhandles = list()
        self._selected = False

        neti = canvas.net_index
        reai = reaction.index
        ctrl = canvas.controller
        # create elements for species
        for gi, sb in gchain(bezier.src_beziers, bezier.dest_beziers):
            dropped_func = self.make_drop_handle_func(ctrl, neti, reai, sb.node_idx, not gi)
            el = BezierHandle(sb.handle, handle_layer,
                              bezier.make_handle_moved_func(sb), dropped_func, reaction, sb.node_idx)
            self.bhandles.append(el)

        def centroid_handle_dropped(p: Vec2):
            ctrl.start_group()
            ctrl.set_center_handle(neti, reai, reaction.src_c_handle.tip)
            post_event(DidCommitDragEvent())
            ctrl.end_group()

        src_bh = BezierHandle(reaction.src_c_handle, handle_layer,
                              lambda _: bezier.src_handle_moved(),
                              centroid_handle_dropped, reaction, -1)
        dest_bh = BezierHandle(reaction.dest_c_handle, handle_layer,
                               lambda _: bezier.dest_handle_moved(),
                               centroid_handle_dropped, reaction, -2)
        src_bh.twin = dest_bh
        dest_bh.twin = src_bh
        self.bhandles.append(src_bh)
        self.bhandles.append(dest_bh)
        center_layers = layer_above(handle_layer, count=2)
        self.center_el = ReactionCenter(self, center_layers)

    def make_drop_handle_func(self, ctrl: IController, neti: int, reai: int, nodei: int,
                              is_source: bool):
        if is_source:
            def ret(p):
                ctrl.set_src_node_handle(neti, reai, nodei, p)
                post_event(DidCommitDragEvent())
        else:
            def ret(p):
                ctrl.set_dest_node_handle(neti, reai, nodei, p)
                post_event(DidCommitDragEvent())
        return ret

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, val: bool):
        # Enable/disable Handles based on whether the curve is selected
        self._selected = val
        for bz in self.bhandles:
            bz.enabled = val

    def nodes_moved(self, evt: CanvasEvent):
        """Handler for after a node has moved."""
        # If already moving (i.e. self._dirty_indices is not empty), then skip forward
        c_evt = cast(DidMoveNodesEvent, evt)
        node_indices = c_evt.node_indices
        offset = c_evt.offset
        rects = [self.canvas.node_idx_map[idx].rect for idx in chain(
            self.reaction.sources, self.reaction.targets)]
        self.bezier.nodes_moved(rects)
        if len(self._dirty_indices) == 0:
            self._dirty_indices = {idx for idx in node_indices}
            my_indices = {idx for idx in chain(
                self.reaction.sources, self.reaction.targets)}
            self._moving_all = my_indices <= self._dirty_indices

        neti = 0
        for i, idx in enumerate(node_indices):
            for in_src in [True, False]:
                if (idx, in_src) in self.index_to_bz:
                    bz = self.index_to_bz[(idx, in_src)]
                    off = offset if isinstance(offset, Vec2) else offset[i]
                    bz.handle.tip += off
                    post_event(DidMoveBezierHandleEvent(neti, self.reaction.index, bz.node_idx,
                                                        by_user=True, direct=False))
                    bz.update_curve(self.bezier.real_center)

        if self._moving_all and isinstance(offset, Vec2):
            # Only move src_handle_tip if moving all nodes and they are moved by the same amount.
            self.reaction.src_c_handle.tip += offset
            self.bezier.src_handle_moved()
            post_event(DidMoveBezierHandleEvent(neti, self.reaction.index, -1, by_user=True,
                                                direct=False))

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

    def on_mouse_enter(self, logical_pos: Vec2):
        self.on_mouse_move(logical_pos)

    def on_left_down(self, logical_pos: Vec2) -> bool:
        return True  # Return True so that this can be selected

    def on_paint(self, gc: wx.GraphicsContext):
        self.bezier.do_paint(gc, self.reaction.fill_color, self.selected)


class CompartmentElt(CanvasElement):
    def __init__(self, compartment: Compartment, major_layer: int, minor_layer: int):
        super().__init__((major_layer, minor_layer))
        self.compartment = compartment

    def pos_inside(self, logical_pos: Vec2) -> bool:
        return pt_in_rect(logical_pos, self.compartment.rect * cstate.scale)

    def on_left_down(self, logical_pos: Vec2) -> bool:
        return True

    def on_paint(self, gc: wx.GraphicsContext, highlight=False):
        rect = Rect(self.compartment.position,
                    self.compartment.size) * cstate.scale
        border = self.compartment.border
        fill = self.compartment.fill
        if highlight:
            # need to reset alpha
            border = change_opacity(border.ChangeLightness(130), border.Alpha())
            fill = change_opacity(fill.ChangeLightness(130), fill.Alpha())
        draw_rect(gc, rect, border=border,
                  border_width=self.compartment.border_width, fill=fill, corner_radius=get_theme('comp_corner_radius'))


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

    Note:
        The behavior of the SelectBox depends on the nodes and compartments selected, but not the
        reactions. The cases of behaviors are documented here:

        1) Only compartments are selected. Nodes within these compartments are dragged along with
           them, but they are not resized.
        3) Only nodes are selected, and they are all in the same compartment. In this case, the
           nodes may be moved normally. They also may be moved outside of their compartment to be
           assigned to another compartment (this is the only case where this is possible). However
           note that the nodes may not be resized to be larger than the containing compartment.
        3) Otherwise, there are two cases depending on if the selected nodes are in the union of
           the selected compartments.
            a) If the selected nodes are entirely contained in the list of selected compartments,
               then everything is moved and resized together, as usual.
            b) Otherwise (i.e. some node is not in any selected compartment), then dragging and
               resizing are disabled.
        Note that in case 2), if all selected nodes are in the base compartment (i.e. no
        compartment), then the base compartment is assumed to be selected, and resizing and moving
        work as usual.
    """
    CURSOR_TYPES = [wx.CURSOR_SIZENWSE, wx.CURSOR_SIZENS, wx.CURSOR_SIZENESW, wx.CURSOR_SIZEWE,
                    wx.CURSOR_SIZENWSE, wx.CURSOR_SIZENS, wx.CURSOR_SIZENESW, wx.CURSOR_SIZEWE]
    HANDLE_MULT = [Vec2(), Vec2(1/2, 0), Vec2(1, 0), Vec2(1, 1/2),
                   Vec2(1, 1), Vec2(1/2, 1), Vec2(0, 1), Vec2(0, 1/2)]

    nodes: List[Node]
    node_indices: List[int]
    compartments: List[Compartment]
    comp_indices: List[int]
    # List of nodes that are not selected, but are within selected compartments. Used only
    # for SMode.CONTAINED
    peripheral_nodes: List[Node]
    related_elts: List[CanvasElement]
    bounding_rect: Rect
    _padding: float  #: padding for the bounding rectangle around the selected nodes
    _drag_rel: Vec2  #: relative position of the mouse to the bounding rect when dragging started
    #: whether the node was drag-moved between left_down and left_up.
    _did_move: bool
    _orig_rpos: List[Vec2]  #: relative positions of the comps and nodes to the select box
    _orig_rsize: List[Vec2]  #: sizes of the comps and nodes to the select box
    #: relative positions of the compartments and nodes to cursor; updated when dragging starts
    _rel_positions: List[Vec2]
    _resize_handle: int  #: the node resize handle.
    node_min_ratio: Optional[Vec2]
    comp_min_ratio: Optional[Vec2]
    #: the minimum resize ratio for each axis, to avoid making the nodes too small
    _min_resize_ratio: Vec2
    #: the bounding rect when dragging/resizing started
    _orig_rect: Optional[Rect]
    _bounds: Rect  #: the bounds that the bounding rect may not exceed
    special_mode: SelectBox.SMode

    class Mode(enum.Enum):
        IDLE = 0
        MOVING = 1
        RESIZING = 2

    class SMode(enum.Enum):
        """For what this does, see "Notes" section of the class documentation."""

        COMP_ONLY = 0
        """Only compartments are selected."""
        NODES_IN_ONE = 1
        """Only nodes are selected, and they are in a single compartment."""
        CONTAINED = 2
        """Nodes are entirely contained in the selected compartments, or they are all in the base
        compartment.
        """
        NOT_CONTAINED = 3
        """Nodes are not entirely contained in the selected compartments."""

    def __init__(self, canvas, nodes: List[Node], compartments: List[Compartment], bounds: Rect,
                 controller: IController, net_index: int, layer: int):
        super().__init__(layer)
        self.canvas = canvas
        self.peripheral_nodes = list()
        self.update(nodes, compartments)
        self.controller = controller
        self.net_index = net_index
        self._mode = SelectBox.Mode.IDLE

        self._drag_rel = Vec2()
        self._did_move = False
        self._orig_rpos = list()
        self._orig_rsizes = list()
        self._rel_positions = list()
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
        self.node_indices = [n.index for n in self.nodes]
        self.comp_indices = [c.index for c in self.compartments]

        if len(nodes) + len(compartments) > 0:
            if len(nodes) == 1 and len(compartments) == 0:
                # If only one node is selected, reduce padding
                self._padding = get_theme('select_outline_padding')
            else:
                self._padding = get_theme('select_box_padding')
            # Align bounding box if only one node is selected, see NodeElement::on_paint for
            # explanations. Note that self._padding should be an integer
            self._padding = int_round(self._padding)
            self.bounding_rect = get_bounding_rect(
                [n.rect for n in nodes] + [c.rect for c in compartments])

        selected_comps = set(c.index for c in compartments) | {-1}
        # Determine SMode
        if len(nodes) == 0:
            self.special_mode = SelectBox.SMode.COMP_ONLY
        else:
            assoc_comps = {n.comp_idx for n in nodes}
            if len(compartments) == 0:
                if len(assoc_comps) == 1:
                    # Nodes are in one compartment
                    self.special_mode = SelectBox.SMode.NODES_IN_ONE
                else:
                    # Cannot possibly contain
                    self.special_mode = SelectBox.SMode.NOT_CONTAINED
            else:
                if selected_comps >= assoc_comps:
                    self.special_mode = SelectBox.SMode.CONTAINED
                else:
                    self.special_mode = SelectBox.SMode.NOT_CONTAINED

        # Compute peripheral nodes
        if self.special_mode == SelectBox.SMode.NOT_CONTAINED:
            self.peripheral_nodes = list()
        else:
            peri_indices = set()
            for comp in compartments:
                if comp.index in selected_comps:
                    peri_indices |= set(comp.nodes)

            peri_indices -= set(n.index for n in nodes)
            self.peripheral_nodes = [self.canvas.node_idx_map[i] for i in peri_indices]

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
        side = get_theme('select_handle_length')
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
        if len(self.nodes) + len(self.compartments) == 0:
            return -2

        rects = self._resize_handle_rects()
        for i, rect in enumerate(rects):
            if pt_in_rect(logical_pos, rect):
                return i

        rects = [n.rect for n in self.nodes] + \
            [c.rect for c in self.compartments]
        if any(pt_in_rect(logical_pos, r * cstate.scale) for r in rects):
            return -1
        else:
            return -2

    def pos_inside(self, logical_pos: Vec2):
        return self._pos_inside_part(logical_pos) != -2

    def on_mouse_enter(self, logical_pos: Vec2):
        self.on_mouse_move(logical_pos)

    def on_mouse_move(self, logical_pos: Vec2):
        self._hovered_part = self._pos_inside_part(logical_pos)
        if self._hovered_part >= 0:
            cursor = SelectBox.CURSOR_TYPES[self._hovered_part]
            self.canvas.SetCursor(wx.Cursor(cursor))
        elif self._hovered_part == -1:
            self.canvas.SetCursor(wx.Cursor(wx.CURSOR_SIZING))
        return True

    def on_mouse_leave(self, logical_pos: Vec2):
        self._hovered_part = -2
        # HACK re-set input_mode with the same value to make canvas update the cursor
        # See issue #9 for details
        cstate.input_mode = cstate.input_mode
        return True

    def on_paint(self, gc: wx.GraphicsContext):
        if len(self.nodes) + len(self.compartments) > 0:
            outline_width = max(even_round(get_theme('select_outline_width')), 2)
            pos, size = self.outline_rect().as_tuple()

            # draw main outline
            draw_rect(gc, Rect(pos, size), border=get_theme('handle_color'),
                      border_width=outline_width, corner_radius=0)

            for handle_rect in self._resize_handle_rects():
                # convert to device position for drawing
                draw_rect(gc, handle_rect, fill=get_theme('handle_color'))

    def map_rel_pos(self, positions: Iterable[Vec2]) -> List[Vec2]:
        temp = [p * cstate.scale - self._orig_rect.position - Vec2.repeat(self._padding)
                for p in positions]
        return temp

    def on_left_down(self, logical_pos: Vec2):
        if len(self.nodes) + len(self.compartments) == 0:
            return False

        # if multi-selecting and clicked on a node/reaction, then the user must mean to de-select
        # that element. In this exceptional case we return False so that canvas can continue the
        # pos_inside loop and find the node/reaction in question later.
        if cstate.multi_select:
            for elt in self.related_elts:
                if elt.pos_inside(logical_pos):
                    return False
        elif len(self.compartments) != 0:
            # make sure that user can select items inside compartment, even if the compartment is
            # itself selected.
            for elt in self.related_elts:
                if elt.pos_inside(logical_pos):
                    if isinstance(elt, ReactionElement):
                        return False
                    elif isinstance(elt, NodeElement) and elt.node.comp_idx != -1:
                        return False
                    else:
                        break

        handle = self._hovered_part
        assert self._mode == SelectBox.Mode.IDLE
        if handle >= 0:
            self._mode = SelectBox.Mode.RESIZING
            self._resize_handle = handle
            # calculate minimum resize ratio, enforcing min size constraints on nodes and comps
            self._update_min_resize_ratio()

            #self._orig_rect = self.outline_rect()
            # Take unaligned bounding rect as orig_rect for better accuracy
            self._orig_rect = padded_rect(
                (self.bounding_rect * cstate.scale), self._padding)
            # relative starting positions to the select box
            orig_node_pos = self.map_rel_pos((n.position for n in self.nodes))
            orig_comp_pos = self.map_rel_pos((c.position for c in self.compartments))
            orig_node_sizes = [n.size * cstate.scale for n in self.nodes]
            orig_comp_sizes = [c.size * cstate.scale for c in self.compartments]
            self._orig_rpos = orig_comp_pos + orig_node_pos
            self._orig_rsizes = orig_comp_sizes + orig_node_sizes
            self._resize_handle_offset = self._resize_handle_pos(handle) - logical_pos
            return True
        elif handle == -1:
            self._mode = SelectBox.Mode.MOVING
            # relative starting positions to the mouse positions
            rel_node_pos = [n.position * cstate.scale - logical_pos for n in self.nodes]
            rel_comp_pos = [c.position * cstate.scale - logical_pos for c in self.compartments]
            self._rel_positions = rel_comp_pos + rel_node_pos
            self._drag_rel = self.bounding_rect.position * cstate.scale - logical_pos
            return True

        return False

    def compute_min_ratio(self) -> Tuple[Optional[Vec2], Optional[Vec2]]:
        """Compute minimum size ratio resizing nodes and compartments.

        Returns:
            A tuple containing (node mininum resize ratio, comp minimum resize ratio). Each ratio
            may be None, in the case that no elements of that type is selected.
        """
        node_min_ratio = None
        comp_min_ratio = None
        if len(self.nodes) != 0:
            min_width = min(n.size.x for n in self.nodes)
            min_height = min(n.size.y for n in self.nodes)
            node_min_ratio = Vec2(get_setting('min_node_width') / min_width,
                                  get_setting('min_node_height') / min_height)

        if len(self.compartments) != 0:
            min_comp_width = min(c.size.x for c in self.compartments)
            min_comp_height = min(c.size.y for c in self.compartments)
            comp_min_ratio = Vec2(get_setting('min_comp_width') / min_comp_width,
                                  get_setting('min_comp_height') / min_comp_height)
            for node in self.peripheral_nodes:
                comp = self.canvas.comp_idx_map[node.comp_idx]
                ratio = node.size.elem_div(comp.size)
                comp_min_ratio = comp_min_ratio.reduce2(max, ratio)

        return node_min_ratio, comp_min_ratio

    def _update_min_resize_ratio(self):
        node_min_ratio, comp_min_ratio = self.compute_min_ratio()

        if node_min_ratio is not None and comp_min_ratio is not None:
            self._min_resize_ratio = node_min_ratio.reduce2(max, comp_min_ratio)
        elif node_min_ratio is not None:
            self._min_resize_ratio = node_min_ratio
        elif comp_min_ratio is not None:
            self._min_resize_ratio = comp_min_ratio
        else:
            assert False, 'Cannot possibly click on handle when nothing is selected.'

    def on_left_up(self, logical_pos: Vec2):
        assert len(self.nodes) + len(self.compartments) != 0
        if self._mode == SelectBox.Mode.MOVING:
            if self._did_move:
                self._did_move = False

                self._commit_move()
        elif self._mode == SelectBox.Mode.RESIZING:
            assert not self._did_move
            self.controller.start_group()
            for node in self.peripheral_nodes:
                self.controller.move_node(self.net_index, node.index, node.position)
            for node in self.nodes:
                self.controller.move_node(self.net_index, node.index, node.position)
                self.controller.set_node_size(self.net_index, node.index, node.size)
            for comp in self.compartments:
                self.controller.move_compartment(self.net_index, comp.index, comp.position)
                self.controller.set_compartment_size(self.net_index, comp.index, comp.size)
                post_event(DidCommitDragEvent())
            self.controller.end_group()

            # Need to do this in case _special_mode == NOT_CONTAINED, so that the mouse has now
            # left the handle. on_mouse_leave is not triggered because it's considered to be dragging.
            self._hovered_part = self._pos_inside_part(logical_pos)
        self._mode = SelectBox.Mode.IDLE

    def on_mouse_drag(self, logical_pos: Vec2, rel_pos: Vec2) -> bool:
        assert self._mode != SelectBox.Mode.IDLE
        rect_data = cast(List[RectData], self.compartments) + cast(List[RectData], self.nodes)
        if self.special_mode == SelectBox.SMode.NOT_CONTAINED:
            # Return True since we still want this to appear to be dragging, just not working.
            return True
        if self._mode == SelectBox.Mode.RESIZING:
            # TODO move the orig_rpos, etc. code to update()
            bounds = self._bounds
            if self.special_mode == SelectBox.SMode.NODES_IN_ONE:
                # constrain resizing to within this compartment
                if self.nodes[0].comp_idx != -1:
                    containing_comp = self.canvas.GetCompartment(self.nodes[0].comp_idx)
                    assert containing_comp is not None
                    bounds = containing_comp.rect

            self._resize(logical_pos, rect_data, self._orig_rpos, self._orig_rsizes, bounds)
        else:
            self._move(logical_pos, rect_data, self._rel_positions)
        return True

    def _resize(self, pos: Vec2, rect_data: List[RectData], orig_pos: List[Vec2],
                orig_sizes: List[Vec2], bounds: Rect):
        """Helper that performs resize on the bounding box, given the logical mouse position."""
        # STEP 1, get new rect vertices
        # see class comment for resize handle format. For side-handles, get the vertex in the
        # counter-clockwise direction
        dragged_idx = self._resize_handle // 2
        # get the vertex opposite dragged idx as fixed_idx
        fixed_idx = int((dragged_idx + 2) % 4)
        orig_dragged_point = self._orig_rect.nth_vertex(dragged_idx)
        cur_dragged_point = self.outline_rect().nth_vertex(dragged_idx)
        fixed_point = self._orig_rect.nth_vertex(fixed_idx)

        target_point = pos + self._resize_handle_offset

        # if a side-handle, then only resize one axis
        if self._resize_handle % 2 == 1:
            if self._resize_handle % 4 == 1:
                # vertical resize; keep x the same
                target_point = target_point.swapped(0, orig_dragged_point.x)
            else:
                assert self._resize_handle % 4 == 3
                target_point = target_point.swapped(1, orig_dragged_point.y)

        # clamp target point
        target_point = clamp_point(target_point, bounds * cstate.scale)

        # STEP 2, get and validate rect ratio

        # raw difference between (current/target) dragged vertex and fixed vertex. Raw as in this
        # is the visual difference shown on the bounding rect.
        orig_diff = orig_dragged_point - fixed_point
        target_diff = target_point - fixed_point

        signs = orig_diff.elem_mul(target_diff)

        # bounding_rect flipped?
        if signs.x < 0:
            target_point = target_point.swapped(0, cur_dragged_point.x)

        if signs.y < 0:
            target_point = target_point.swapped(1, cur_dragged_point.y)

        # take absolute value and subtract padding to get actual difference (i.e. sizing)
        pad_off = Vec2.repeat(self._padding)
        orig_bb_size = (orig_dragged_point -
                        fixed_point).elem_abs() - pad_off * 2
        target_size = (target_point - fixed_point).elem_abs() - pad_off * 2

        size_ratio = target_size.elem_div(orig_bb_size)

        # size too small?
        if size_ratio.x < self._min_resize_ratio.x:
            size_ratio = size_ratio.swapped(0, self._min_resize_ratio.x)

        if size_ratio.y < self._min_resize_ratio.y:
            size_ratio = size_ratio.swapped(1, self._min_resize_ratio.y)

        # re-calculate target_size in case size_ratio changed
        target_size = orig_bb_size.elem_mul(size_ratio)

        # STEP 3 calculate new bounding_rect position and size
        br_pos = Vec2(min(fixed_point.x, target_point.x), min(fixed_point.y, target_point.y))

        # STEP 4 calculate and apply new node positions and sizes
        # calculate and keep incremental ratio for the event arguments
        inc_ratio = orig_bb_size.elem_mul(size_ratio / cstate.scale).elem_div(rect_data[0].size)
        offsets = list()
        index = 0
        for index, (rdata, opos, osize) in enumerate(zip(rect_data, orig_pos, orig_sizes)):
            #assert opos.x >= -1e-6 and opos.y >= -1e-6
            pos = (br_pos + opos.elem_mul(size_ratio) + pad_off) / cstate.scale
            # HACK rect_data is compartments + nodes. So we only append to offsets we've reached
            # the nodes sectoin
            if index >= len(self.compartments):
                offsets.append(pos - rdata.position)
            rdata.position = pos
            rdata.size = osize.elem_mul(size_ratio) / cstate.scale

        # STEP 5 apply new bounding_rect position and size
        self.bounding_rect.position = (br_pos + pad_off) / cstate.scale
        self.bounding_rect.size = target_size / cstate.scale

        # STEP 6 post main events
        if len(self.nodes) != 0:
            post_event(DidResizeNodesEvent(node_indices=self.node_indices, ratio=inc_ratio,
                                           dragged=True))
            post_event(DidMoveNodesEvent(node_indices=self.node_indices,
                                         offset=offsets[len(self.compartments):], dragged=True))
        if len(self.compartments) != 0:
            post_event(DidResizeCompartmentsEvent(
                compartment_indices=self.comp_indices, ratio=inc_ratio, dragged=True))
            post_event(DidMoveCompartmentsEvent(
                compartment_indices=self.comp_indices,
                offset=offsets[:len(self.compartments)], dragged=True))

        # STEP 7 adjust peripheral node positions so that they are inside the compartment
        adjusted_nodes = list()
        offsets = list()
        for node in self.peripheral_nodes:
            assert node.comp_idx != -1
            comp = self.canvas.comp_idx_map[node.comp_idx]
            pos = clamp_rect_pos(node.rect, comp.rect)
            if node.position != pos:
                adjusted_nodes.append(node)
                offsets.append(pos - node.position)
            node.position = pos
        if len(adjusted_nodes) != 0:
            post_event(DidMoveNodesEvent(adjusted_nodes, offsets, dragged=True))

    def _move(self, pos: Vec2, rect_data: List[RectData], rel_positions: List[Vec2]):
        """Helper that performs resize on the bounding box, given the logical mouse position."""
        assert len(rect_data) == len(rel_positions)
        assert len(rect_data) != 0
        # campute tentative new positions. May need to clamp it.
        self._did_move = True
        new_positions = [pos + rp for rp in rel_positions]
        min_x = min(p.x for p in new_positions)
        min_y = min(p.y for p in new_positions)
        max_x = max(p.x + r.size.x * cstate.scale for p,
                    r in zip(new_positions, rect_data))
        max_y = max(p.y + r.size.y * cstate.scale for p,
                    r in zip(new_positions, rect_data))
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
        # The actual amount moved by the rects
        pos_offset = (new_positions[0] + offset) / cstate.scale - rect_data[0].position
        for rdata, np in zip(rect_data, new_positions):
            rdata.position = (np + offset) / cstate.scale

        # Note that don't need to test if out of bounds by peripheral nodes, since all
        # peripheral nodes must be inside selected compartments.
        for node in self.peripheral_nodes:
            node.position += pos_offset

        all_nodes = self.nodes + self.peripheral_nodes
        if len(all_nodes) != 0:
            post_event(DidMoveNodesEvent([n.index for n in all_nodes], pos_offset, dragged=True))
        if len(self.compartments) != 0:
            post_event(DidMoveCompartmentsEvent(compartment_indices=[c.index for c in self.compartments],
                                                offset=pos_offset, dragged=True))
    
    def move_offset(self, offset: Vec2):
        rect_data = cast(List[RectData], self.compartments) + cast(List[RectData], self.nodes)
        pos = self.bounding_rect.position
        rel_node_pos = [n.position * cstate.scale - pos for n in self.nodes]
        rel_comp_pos = [c.position * cstate.scale - pos for c in self.compartments]
        rel_positions = rel_comp_pos + rel_node_pos

        self._move(pos + offset, rect_data, rel_positions)
        self._commit_move()

    def _commit_move(self):
        self.controller.start_group()
        for node in chain(self.nodes, self.peripheral_nodes):
            self.controller.move_node(self.net_index, node.index, node.position)

        for comp in self.compartments:
            self.controller.move_compartment(
                self.net_index, comp.index, comp.position)

        if self.special_mode == SelectBox.SMode.NODES_IN_ONE:
            compi = self.canvas.InWhichCompartment(self.nodes)
            old_compi = self.nodes[0].comp_idx
            if compi != old_compi:
                for node in self.nodes:
                    self.controller.set_compartment_of_node(
                        self.net_index, node.index, compi)
                post_event(DidChangeCompartmentOfNodesEvent(
                    node_indices=[n.index for n in self.nodes],
                    old_compi=old_compi,
                    new_compi=compi
                ))

        post_event(DidCommitDragEvent())
        self.controller.end_group()
