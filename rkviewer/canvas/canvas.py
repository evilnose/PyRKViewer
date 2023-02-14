"""The main canvas panel.

This handles user input actions, updates the model, and performs redraws after the model is updated.
"""
# pylint: disable=maybe-no-member
from collections import defaultdict
from contextlib import contextmanager
import copy
import enum
from itertools import chain
import logging
from logging import Logger
import time
import typing
from typing import Collection, DefaultDict, Dict, Iterable, List, Optional, Set, Tuple, Union, cast
from commentjson.commentjson import JSONLibraryException
from marshmallow.exceptions import ValidationError

from sortedcontainers import SortedKeyList
import wx
import os
import math

from ..config import get_setting, get_theme, pop_settings_err
from ..events import (
    CanvasDidUpdateEvent,
    DidCommitDragEvent, DidDeleteEvent, DidMoveNodesEvent,
    DidPaintCanvasEvent,
    SelectionDidUpdateEvent,
    bind_handler,
    post_event,
)
from ..mvc import IController
from ..utils import even_round, opacity_mul, resource_path
from .data import Compartment, Node, Reaction, ReactionBezier, compute_centroid, init_bezier
from .elements import BezierHandle, CanvasElement, CompartmentElt, Layer, NodeElement, ReactionCenter, ReactionElement, SelectBox, layer_above
from .geometry import (
    Rect, Vec2, circle_bounds,
    clamp_rect_pos, get_bounding_rect,
    padded_rect,
    rects_overlap,
    pt_in_rect,
)
from .overlays import CanvasOverlay, Minimap
from .state import InputMode, cstate
from .utils import Observer, SetSubject, default_handle_positions
from .utils import draw_rect, get_nodes_by_idx


BOUNDS_EPS = 0
"""The padding around the canvas to ensure nodes are not moved out of bounds due to floating pont
issues.
"""
BOUNDS_EPS_VEC = Vec2.repeat(BOUNDS_EPS)
"""2D bounds vector formed from BOUNDS_EPS"""


class Alignment(enum.Enum):
    """Alignment"""
    LEFT = 0
    RIGHT = 1
    CENTER = 2
    TOP = 3
    BOTTOM = 4
    MIDDLE = 5
    GRID = 6
    HORIZONTAL = 7  #: Arrange into a row
    VERTICAL = 8  #: Arrange into a column


# Don't use ScrolledPanel since Canvas does not scroll conventionally.
class Canvas(wx.ScrolledWindow):
    """The main window onto which nodes, reactions, etc. will be drawn.

    Attributes:
        MIN_ZOOM_LEVEL: The minimum zoom level the user is allowed to reach. See SetZoomLevel() for more detail.
        MAX_ZOOM_LEVEL: The maximum zoom level the user is allowed to reach.
        NODE_LAYER: The node layer.
        REACTION_LAYER: The reaction layer.
        SELECT_BOX_LAYER: The layer for the select box.

        controller: The associated controller instance.
        realsize: The actual, total size of canvas, including the part offscreen.
        net_index: The index of the current network. Rightn now it can be zero.
        sel_nodes_idx: The set of indices of the currently selected nodes.
        sel_reactions_idx: The set of indices of the currently selected reactions.
        sel_compartments_idx: The set of indices of the currently selected compartments.
        drag_sel_nodes_idx: The set of indices tentatively selected during dragging. This is added
                           to sel_nodes_idx only after the user has stopped drag-selecting.
        drag_sel_comps_idx: See drag_sel_nodes_idx but for compartments
        hovered_element: The element over which the mouse is hovering, or None.
        zoom_slider: The zoom slider widget.
        reaction_map: Maps node index to the set of reaction (indices) that it is in.
    """
    MIN_ZOOM_LEVEL: int = -11
    MAX_ZOOM_LEVEL: int = 11
    NODE_LAYER = 1
    REACTION_LAYER = 2
    COMPARTMENT_LAYER = 3
    DRAGGED_NODE_LAYER = 9
    SELECT_BOX_LAYER = 10
    HANDLE_LAYER = 11
    MILLIS_PER_REFRESH = 16  # serves as framerate cap
    KEY_MOVE_STRIDE: int = 1  #: Number of pixels to move when the user presses an arrow key.
    #: Larger move stride for convenience; used when SHIFT is pressed.
    KEY_MOVE_LONG_STRIDE: int = 10

    controller: IController
    realsize: Vec2
    sel_nodes_idx: SetSubject
    sel_reactions_idx: SetSubject
    sel_compartments_idx: SetSubject
    drag_sel_nodes_idx: Set[int]
    drag_sel_rxns_idx: Set[int]
    drag_sel_comps_idx: Set[int]
    hovered_element: Optional[CanvasElement]
    dragged_element: Optional[CanvasElement]
    zoom_slider: wx.Slider
    reaction_map: DefaultDict[int, Set[int]]  # maps node index to reactions it's part of
    logger: Logger

    #: Current network index. Right now this is always 0 since there is only one tab.
    _net_index: int
    _nodes: List[Node]  #: List of Node instances. This contains data needed to render them.
    # TODO move this one to top docstring
    _reactions: List[Reaction]  #: List of ReactionBezier instances.
    _compartments: List[Compartment]  #: List of Compartment instances
    _node_elements: List[NodeElement]
    _reaction_elements: List[ReactionElement]
    _compartment_elements: List[CompartmentElt]
    _plugin_elements: Set[CanvasElement]
    _zoom_level: int  #: The current zoom level. See SetZoomLevel() for more detail.
    #: The zoom scale. This always corresponds one-to-one with zoom_level. See property for detail.
    _reactant_idx: Set[int]  #: The list of indices of the currently designated reactant nodes.
    _product_idx: Set[int]  #: The list of indices of the currently designated product nodes
    _select_box: SelectBox  #: The select box element.
    _minimap: Minimap  #: The minimap overlay.
    _overlays: List[CanvasOverlay]  #: The list of overlays. Used when processing click events.
    _drag_selecting: bool  #: If currently dragging the selection rectangle.
    _drag_select_start: Vec2  #: The (logical) mouse position when the user started drag selecting.
    _drag_rect: Rect  #: The current drag-selection rectangle.
    _reverse_status: Dict[str, int]  #: Maps status string in .config.settings to its index.
    #: Flag for whether the mouse is currently outside of the root app window.
    _copied_nodes: List[Node]  #: Copy of nodes currently in clipboard
    _accum_frames: int
    _last_fps_update: int
    _last_refresh: int
    #: When True, SelectionDidUpdate events are not fired. This is in case multiple such events
    #: are fired consecutively (e.g. both nodes and reactions changed), to make sure that only one
    #: event fires in total.
    _in_selection_group: bool
    #: bool to indicate whether a selection changed event was fired inside selection group.
    _selection_dirty: bool
    node_idx_map: Dict[int, Node]  #: Maps node index to node
    reaction_idx_map: Dict[int, Reaction]  #: Maps reaction index to reaction
    node_to_rxn: DefaultDict[int, Set[int]]
    comp_idx_map: Dict[int, Compartment]  #: Maps compartment index to compartment
    sel_nodes: List[Node]  #: Current list of selected nodes; cached for performance
    sel_reactions: List[Reaction]
    sel_comps: List[Compartment]  #: Current list of selected comps; cached for performance
    drawing_drag: bool  #: See self._UpdateSelectedLists() for more details


    def __init__(self, controller: IController, zoom_slider, *args, realsize: Tuple[int, int],  **kw):
        # ensure the parent's __init__ is called
        super().__init__(*args, style=wx.DEFAULT_FRAME_STYLE & ~wx.MAXIMIZE_BOX ^ wx.RESIZE_BORDER,
                         **kw)
        self.last_motion = 0
        err = pop_settings_err()
        if err is not None:
            if isinstance(err, JSONLibraryException):
                message = 'Failed when parsing settings.json. Using default settings instead.\n\n'
                message += err.message
            else:
                message = 'Invalid settings in settings.json. Using default settings instead.\n\n'
                message += str(err)
            self.ShowWarningDialog(message)

        init_bezier()
        self.controller = controller
        self._net_index = 0
        self._nodes = list()
        self._reactions = list()
        self._compartments = list()
        self._node_elements = list()
        self._reaction_elements = list()
        self._compartment_elements = list()
        # TODO document below
        self._model_elements = SortedKeyList(key=lambda e: e.layers)
        self._widget_elements = SortedKeyList(key=lambda e: e.layers)
        self._plugin_elements = set()
        self.hovered_element = None
        self.dragged_element = None
        self.node_to_rxn = defaultdict(set)
        self.logger = logging.getLogger('canvas')

        # prevent flickering
        self.SetDoubleBuffered(True)

        # events
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SCROLLWIN, self.OnScroll)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnWindowDestroy)
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda _: None)  # Don't erase background
        self.Bind(wx.EVT_CHAR_HOOK, self.OnChar)

        bind_handler(DidCommitDragEvent, self.OnDidCommitNodePositions)

        # state variables
        cstate.input_mode = InputMode.SELECT
        # Set to (0, 0) since this won't be used before it's updated once first
        self._dragged_rel_window = wx.Point()

        self._zoom_level = 0
        self.realsize = Vec2(realsize)
        cstate.bounds = Rect(Vec2(), self.realsize)
        scroll_width = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
        scroll_height = wx.SystemSettings.GetMetric(wx.SYS_HSCROLL_Y)
        self._scroll_off = Vec2(scroll_width, scroll_height)
        self.SetVirtualSize(*self.realsize)

        bounds = Rect(BOUNDS_EPS_VEC, self.realsize - BOUNDS_EPS_VEC)
        self._select_box = SelectBox(self, [], [], bounds, self.controller, self._net_index,
                                     Canvas.SELECT_BOX_LAYER)
        self.sel_nodes_idx = SetSubject()
        self.sel_reactions_idx = SetSubject()
        self.sel_compartments_idx = SetSubject()
        selection_obs = Observer(lambda _: self._SelectionChanged())
        self.sel_nodes_idx.attach(selection_obs)
        self.sel_reactions_idx.attach(selection_obs)
        self.sel_compartments_idx.attach(selection_obs)
        self._reactant_idx = set()
        self._product_idx = set()

        self.zoom_slider = zoom_slider
        self.zoom_slider.SetRange(Canvas.MIN_ZOOM_LEVEL, Canvas.MAX_ZOOM_LEVEL)
        self.zoom_slider.SetBackgroundColour(get_theme('zoom_slider_bg'))
        self.GetParent().Bind(wx.EVT_SLIDER, self.OnSlider)

        # Set a placeholder value for position; we will set it later in SetOverlayPositions().
        self._minimap = Minimap(pos=Vec2(), device_pos=Vec2(), width=200, realsize=self.realsize,
                                window_size=Vec2(self.GetSize()), pos_callback=self.SetOriginPos)

        self._overlays = [self._minimap]

        self._drag_selecting = False
        self._drag_select_start = Vec2()
        self._drag_rect = Rect(Vec2(), Vec2())
        self.drag_sel_nodes_idx = set()
        self.drag_sel_rxns_idx = set()
        self.drag_sel_comps_idx = set()

        self._status_bar = self.GetTopLevelParent().GetStatusBar()
        assert self._status_bar is not None, "Need to create status bar before creating canvas!"

        status_fields = get_setting('status_fields')
        assert status_fields is not None
        self._reverse_status = {name: i for i, (name, _) in enumerate(status_fields)}

        self._copied_nodes = list()

        wx.CallAfter(lambda: self.SetZoomLevel(0, Vec2(0, 0)))

        self._accum_frames = 0
        self._cursor_logical_pos = None
        self._last_fps_update = 0
        self._last_refresh = 0
        cstate.input_mode_changed = self.InputModeChanged
        self.comp_index = 0  # Compartment of index; remove once controller implements compartments
        self.node_idx_map = dict()
        self.reaction_idx_map = dict()
        self.comp_idx_map = dict()

        self._nodes_floating = False
        self._in_selection_group = False
        self._selection_dirty = False

        self.SetOverlayPositions()
        self.sel_nodes = []
        self.sel_reactions = []
        self.sel_comps = []
        self.drawing_drag = False

        self._dynamic_elements = set()
        self._static_bitmap = None
        self._dirty = True

    def OnWindowDestroy(self, evt):
        evt.Skip()

    def OnIdle(self, evt):
        # if self._static_bitmap is None:
        #     self._RedrawDynamicToBuffer()
        self.LazyRefresh()

    def OnChar(self, evt):
        keycode = evt.GetKeyCode()

        offset: Vec2
        if keycode == wx.WXK_LEFT:
            offset = Vec2(-1, 0)
        elif keycode == wx.WXK_RIGHT:
            offset = Vec2(1, 0)
        elif keycode == wx.WXK_UP:
            offset = Vec2(0, -1)
        elif keycode == wx.WXK_DOWN:
            offset = Vec2(0, 1)
        else:
            evt.Skip()
            return

        if wx.GetKeyState(wx.WXK_SHIFT):
            offset *= Canvas.KEY_MOVE_LONG_STRIDE
        else:
            offset *= Canvas.KEY_MOVE_STRIDE
        if len(self._select_box.nodes) != 0 or len(self._select_box.compartments) != 0:
            self._select_box.move_offset(offset)

    @property
    def select_box(self):
        return self._select_box

    @property
    def nodes(self):
        return self._nodes

    @property
    def reactions(self):
        return self._reactions

    @property
    def compartments(self):
        return self._compartments

    def InputModeChanged(self, val: InputMode):
        if val == InputMode.ADD_NODES:
            self.SetCursor(wx.Cursor(wx.CURSOR_CROSS))
        else:
            self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

        self._SetStatusText('mode', str(val))

    @property
    def net_index(self):
        return self._net_index

    def ArrowTipChanged(self):
        for rea_el in self._reaction_elements:
            for bz in rea_el.bezier.dest_beziers:
                bz.arrow_tip_changed()
        self._RedrawDynamicToBuffer()

    def RegisterAllChildren(self, widget):
        """Connect all descendants of this widget to relevant events.

        wxPython does not propagate events like LEFT_UP and MOTION up to the
        parent of the window that received it. Therefore normally there is
        no way for DragDrop to detect a mouse event if it occurred on top
        of a child widget of window. This function solves this problem by
        recursively connecting all child widgets of window to trigger the DragDrop
        handlers. Note that whatever event registered here must do evt.Skip() so
        that the child itself can handle its event as well.

        This solution is from https://stackoverflow.com/a/27911300/9171534
        """
        if self != widget:
            widget.Connect(wx.ID_ANY, -1, wx.wxEVT_LEFT_UP, self.OnLeftUp)
            widget.Connect(wx.ID_ANY, -1, wx.wxEVT_MOTION, self.OnMotion)
            widget.Connect(wx.ID_ANY, -1, wx.wxEVT_LEAVE_WINDOW, self.OnLeaveWindow)

        for child in widget.GetChildren():
            self.RegisterAllChildren(child)

    def _InWhichOverlay(self, device_pos: Vec2) -> Optional[CanvasOverlay]:
        """If position is within an overlay, return that overlay; otherwise return None.

        Note:
            If the position is within multiple overlays, return the latest added overlay, i.e. the
            overlay with the largest index in the _overlays list.

        Returns:
            An overlay if applicable, or None if not.
        """
        # TODO right now this is hardcoded; in the future add List[CanvasOverlay] attribute
        if pt_in_rect(device_pos, Rect(self._minimap.device_pos, self._minimap.size)):
            return self._minimap
        return None

    def SetOverlayPositions(self):
        """Set the positions of the overlaid widgets.

        This should be called in OnPaint so that the overlaid widgets stay in the same relative
        position.
        """
        # do all the minimap updates here, since this is simpler and less prone to bugs
        minimap_pos = Vec2(self.GetClientSize()) - self._minimap.size
        minimap_pos = minimap_pos.swapped(1, minimap_pos.y)
        self._minimap.device_pos = minimap_pos
        self._minimap.position = Vec2(self.CalcUnscrolledPosition(*minimap_pos.as_int()))
        self._minimap.window_pos = Vec2(self.CalcUnscrolledPosition(0, 0)) / cstate.scale
        self._minimap.window_size = Vec2(self.GetSize()) / cstate.scale
        self._minimap.realsize = self.realsize

    def CreateNodeElement(self, node: Node, layers: Layer) -> NodeElement:
        return NodeElement(node, self, layers)

    def CreateReactionElement(self, rxn: Reaction, layers: Layer) -> ReactionElement:
        snodes = [self.node_idx_map[idx] for idx in rxn.sources]
        tnodes = [self.node_idx_map[idx] for idx in rxn.targets]
        rb = ReactionBezier(rxn, snodes, tnodes)
        return ReactionElement(rxn, rb, self, layers, Canvas.HANDLE_LAYER)

    def CreateCompartmentElement(self, comp: Compartment) -> CompartmentElt:
        # NOTE the index of the compartment is used as its *secondary layer*, i.e. all compartments
        # share the same main layor (COMPARTMENT_LAYER), but to make sure the containing nodes
        # are rendered correctly, a secondary layer is applied to each compartment, taking its
        # index. This works because compartments with higher indices are added later and therefore
        # should be rendered on top.
        return CompartmentElt(comp, Canvas.COMPARTMENT_LAYER, comp.index)

    def Reset(self, nodes: List[Node], reactions: List[Reaction], compartments: List[Compartment]):
        """Update the list of nodes and apply the current scale."""
        # destroy old elements
        for elt in chain(self._model_elements, self._widget_elements):
            if elt not in self._plugin_elements:
                elt.destroy()

        # cull removed indices
        node_idx = {n.index for n in nodes}
        rxn_idx = {r.index for r in reactions}
        comp_idx = {c.index for c in compartments}

        self.sel_nodes_idx.set_item(self.sel_nodes_idx.item_copy() & node_idx)
        new_sel_reactions = self.sel_reactions_idx.item_copy() & rxn_idx
        self.sel_reactions_idx.set_item(new_sel_reactions)
        self.sel_compartments_idx.set_item(self.sel_compartments_idx.item_copy() & comp_idx)

        self._reactant_idx &= node_idx
        self._product_idx &= node_idx

        # Update index maps
        self.node_idx_map = dict()
        for node in nodes:
            self.node_idx_map[node.index] = node
        self.reaction_idx_map = dict()
        for rxn in reactions:
            self.reaction_idx_map[rxn.index] = rxn
        self.comp_idx_map = dict()
        for comp in compartments:
            self.comp_idx_map[comp.index] = comp

        # Update reaction map
        self.node_to_rxn = defaultdict(set)
        for rxn in reactions:
            for nodei in chain(rxn.sources, rxn.targets):
                self.node_to_rxn[nodei].add(rxn.index)

        self._nodes = nodes
        self._reactions = reactions
        self._compartments = compartments
        # Don't clear hovered_element if it is SelectBox
        if not isinstance(self.hovered_element, SelectBox):
            self.hovered_element = None
        self.dragged_element = None

        self._compartment_elements = [self.CreateCompartmentElement(c) for c in compartments]
        # create node elements and assign the correct layers to them (accounting for compartments)
        self._node_elements = list()
        for node in nodes:
            compi = self.controller.get_compartment_of_node(self.net_index, node.index)
            layers = Canvas.NODE_LAYER if compi == -1 else (Canvas.COMPARTMENT_LAYER, compi, 1)
            self._node_elements.append(self.CreateNodeElement(node, layers))

        # create reaction elements and assign the correct layers
        self._reaction_elements = list()
        for rxn in reactions:
            related_nodes = set(chain(rxn.sources, rxn.targets))
            top_layer = max(
                el.layers for el in self._node_elements if el.node.index in related_nodes)
            # Make sure reaction is displayed above its top-most node
            self._reaction_elements.append(self.CreateReactionElement(rxn, layer_above(top_layer)))

        # Initialize elements list
        select_elements = cast(List[CanvasElement], self._node_elements) + cast(
            List[CanvasElement], self._reaction_elements) + cast(
                List[CanvasElement], self._compartment_elements)
        for rxn_el in self._reaction_elements:
            # Add Bezier handle and center elements
            select_elements += rxn_el.bhandles
            select_elements.append(rxn_el.center_el)
            # Update reactions on whether they are selected
            rxn_el.selected = rxn_el.reaction.index in new_sel_reactions

        for plugin_el in self._plugin_elements:
            select_elements.append(plugin_el)

        self._model_elements = SortedKeyList(select_elements, lambda e: e.layers)
        self._select_box.update(self.GetSelectedNodes(),
                                [c for c in self._compartments if self.sel_compartments_idx.contains(c.index)])
        self._UpdateSelectBoxLayer()
        self._select_box.related_elts = select_elements
        self._widget_elements = SortedKeyList([self._select_box], lambda e: e.layers)
        self._minimap.elements = self._model_elements

        self._UpdateSelectedLists()
        self.FullRedraw()

        post_event(CanvasDidUpdateEvent())

    def GetCompartment(self, comp_idx: int) -> Optional[Compartment]:
        for comp in self._compartments:
            if comp.index == comp_idx:
                return comp

        return Optional[None]

    def _SetStatusText(self, name: str, text: str):
        idx = self._reverse_status[name]
        self._status_bar.SetStatusText(text, idx)

    def SetOriginPos(self, pos: Vec2):
        """Set the origin position (position of the topleft corner) to pos by scrolling."""
        # check if out of bounds
        pos = pos.map(lambda e: max(e, 0))

        limit = self.realsize * cstate.scale - Vec2(self.GetSize())
        pos = pos.reduce2(min, limit)

        pos = pos.elem_div(Vec2(self.GetScrollPixelsPerUnit()))
        # need to mult by scale here since self.VirtualPosition is artificially increased, per
        # scale * self.realsize
        #self.Scroll(*pos)
        pos_list = list(pos)
        pos_list = [int(pos_item) for pos_item in pos_list]
        self.Scroll(*pos_list)
        self.SetOverlayPositions()

    @property
    def zoom_level(self) -> int:
        return self._zoom_level

    def SetZoomLevel(self, zoom: int, anchor: Vec2):
        """Zoom in/out with the given anchor.

        The anchor point stays at the same relative position after
        zooming. Note that the anchor position is scrolled position,
        i.e. device position
        """
        if zoom < Canvas.MIN_ZOOM_LEVEL or zoom > Canvas.MAX_ZOOM_LEVEL:
            raise ValueError('Zoom level must be between {} and {}. Got {} instead.',
                             Canvas.MIN_ZOOM_LEVEL, Canvas.MAX_ZOOM_LEVEL, zoom)
        self._zoom_level = zoom
        old_scale = cstate.scale
        cstate.scale = 1.2 ** zoom

        # adjust scroll position
        logical = Vec2(self.CalcUnscrolledPosition(anchor.to_wx_point()))
        scaled = logical * (cstate.scale / old_scale)
        newanchor = Vec2(self.CalcScrolledPosition(scaled.to_wx_point()))
        # the amount of shift needed to keep anchor at the same position
        shift = newanchor - anchor
        cur_scroll = Vec2(self.CalcUnscrolledPosition(0, 0))
        new_scroll = cur_scroll + shift
        # convert to scroll units
        new_scroll = new_scroll.elem_div(Vec2(self.GetScrollPixelsPerUnit()))

        vsize = self.realsize * cstate.scale
        self.SetVirtualSize(int(vsize.x), int(vsize.y))

        # Important: set virtual size first, then scroll
        self.Scroll(int(new_scroll.x), int(new_scroll.y))

        self.zoom_slider.SetValue(self._zoom_level)
        self.zoom_slider.SetPageSize(2)

        self._SetStatusText('zoom', '{:.2f}x'.format(cstate.scale))

        self.FullRedraw()

    def ZoomCenter(self, zooming_in: bool):
        """Zoom in on the center of the visible window."""
        self.IncrementZoom(zooming_in, Vec2(self.GetSize()) / 2)

    def IncrementZoom(self, zooming_in: bool, anchor: Vec2):
        """Zoom in/out by one step on the anchor, if within zoom range."""
        new_zoom = self._zoom_level + (1 if zooming_in else -1)
        if new_zoom < self.MIN_ZOOM_LEVEL or new_zoom > self.MAX_ZOOM_LEVEL:
            return
        self.SetZoomLevel(new_zoom, anchor)

    def ResetZoom(self):
        """Reset the zoom level, with the anchor on the center of the visible window."""
        self.SetZoomLevel(0, Vec2(self.GetSize()) / 2)

    def FitNodeSizeToText(self):
        dc = wx.WindowDC(self)
        gc = wx.GraphicsContext.Create(dc)
        min_w = get_theme('node_width')
        min_h = get_theme('node_height')
        with self.controller.group_action():
            for node in self.nodes:
                # TODO set font
                tp = node.composite_shape.text_item[0]
                font = wx.Font(wx.FontInfo(tp.font_size)
                               .Family(tp.font_family)
                               .Style(tp.font_style)
                               .Weight(tp.font_weight))
                gfont = gc.CreateFont(font)
                gc.SetFont(gfont)
                w, h, _, _ = gc.GetFullTextExtent(node.id)
                w += 20
                h += 10
                w = max(w, min_w)
                h = max(h, min_h)
                self.controller.set_node_size(self.net_index, node.index, Vec2(w, h))

    def _GetUniqueName(self, base: str, names: Collection[str], *args: Collection[str]) -> str:
        """Given a base name "x", try "x_0", "x_1", ... until it is unique in all the collections.
        """
        increment = 0
        # keep incrementing as long as there is duplicate ID
        while True:
            suffix = '_{}'.format(increment)

            cur_id = base + suffix

            if cur_id in names:
                increment += 1
                continue

            for arg in args:
                if cur_id in arg:
                    increment += 1
                    break
            else:
                # loop finished normally; done
                return cur_id

    def OnLeftDown(self, evt):
        try:
            device_pos = Vec2(evt.GetPosition())
            logical_pos = Vec2(self.CalcUnscrolledPosition(evt.GetPosition())) / cstate.scale

            # Check if clicked on overlay using device_pos
            overlay = self._InWhichOverlay(device_pos)
            if overlay is not None:
                overlay.hovering = True
                overlay.OnLeftDown(device_pos)
                return

            for ol in self._overlays:
                if ol is not overlay and ol.hovering:
                    ol.hovering = False

            if cstate.input_mode == InputMode.SELECT:
                for el in self._ElementsHighToLow():
                    if not el.enabled:
                        continue
                    if el.pos_inside(logical_pos) and el.on_left_down(logical_pos):
                        self.dragged_element = el
                        self._last_drag_pos = logical_pos
                        break
                else:
                    self.dragged_element = None

                # variables for keeping track if clicked on a selectable element
                node: Optional[Node] = None
                rxn: Optional[Reaction] = None
                comp: Optional[Compartment] = None
                rxn_center: Optional[ReactionCenter] = None
                if isinstance(self.dragged_element, NodeElement):
                    n_elem = typing.cast(NodeElement, self.dragged_element)
                    node = n_elem.node
                elif isinstance(self.dragged_element, ReactionElement):
                    r_elem = typing.cast(ReactionElement, self.dragged_element)
                    rxn = r_elem.reaction
                elif isinstance(self.dragged_element, CompartmentElt):
                    c_elem = typing.cast(CompartmentElt, self.dragged_element)
                    comp = c_elem.compartment
                elif isinstance(self.dragged_element, ReactionCenter):
                    rxn_center = typing.cast(ReactionCenter, self.dragged_element)
                    rxn = rxn_center.parent.reaction

                # not resizing or dragging
                if cstate.multi_select:
                    if rxn is not None:
                        if self.sel_reactions_idx.contains(rxn.index):
                            self.sel_reactions_idx.remove(rxn.index)
                        else:
                            self.sel_reactions_idx.add(rxn.index)
                    elif node is not None:
                        if self.sel_nodes_idx.contains(node.index):
                            self.sel_nodes_idx.remove(node.index)
                        else:
                            self.sel_nodes_idx.add(node.index)
                    elif comp is not None:
                        if self.sel_compartments_idx.contains(comp.index):
                            self.sel_compartments_idx.remove(comp.index)
                        else:
                            self.sel_compartments_idx.add(comp.index)
                else:
                    with self._SelectGroupEvent():
                        if rxn is not None:
                            self.sel_reactions_idx.set_item({rxn.index})
                            self.sel_nodes_idx.set_item(set())
                            self.sel_compartments_idx.set_item(set())
                        elif node is not None:
                            self.sel_nodes_idx.set_item({node.index})
                            self.sel_reactions_idx.set_item(set())
                            self.sel_compartments_idx.set_item(set())
                        elif comp is not None:
                            self.sel_nodes_idx.set_item(set())
                            self.sel_reactions_idx.set_item(set())
                            self.sel_compartments_idx.set_item({comp.index})
                        elif self.dragged_element is None:
                            # clear selected nodes
                            self.sel_nodes_idx.set_item(set())
                            self.sel_reactions_idx.set_item(set())
                            self.sel_compartments_idx.set_item(set())

                if not cstate.multi_select:
                    # if clicked on a new node/compartment, immediately allow dragging on the
                    # updated select box
                    if (node or comp) and self._select_box.pos_inside(logical_pos):
                        self._select_box.on_mouse_enter(logical_pos)
                        good = self._select_box.on_left_down(logical_pos)
                        assert good
                        self.dragged_element = self._select_box
                        self.hovered_element = self._select_box
                        self._FloatNodes()
                        return

                # clicked on nothing; drag-selecting
                if self.dragged_element is None:
                    self._drag_selecting = True
                    self._drag_select_start = logical_pos
                    self._drag_rect = Rect(self._drag_select_start, Vec2())
                    self.drag_sel_nodes_idx = set()
                    self.drag_sel_rxns_idx = set()
                    self.drag_sel_comps_idx = set()
                elif isinstance(self.dragged_element, SelectBox):
                    self._FloatNodes()
            elif cstate.input_mode == InputMode.ADD_NODES:
                size = Vec2(get_theme('node_width'), get_theme('node_height'))

                unscaled_pos = logical_pos
                adj_pos = unscaled_pos - size / 2

                node = Node(
                    'x',
                    self.net_index,
                    pos=adj_pos,
                    size=size,
                    # fill_color=get_theme('node_fill'),
                    # border_color=get_theme('node_border'),
                    # border_width=get_theme('node_border_width'),
                    comp_idx=self.RectInWhichCompartment(Rect(adj_pos, size)),
                    floatingNode=True,
                    lockNode=False,
                )
                node.position = clamp_rect_pos(node.rect, Rect(Vec2(), self.realsize), BOUNDS_EPS)
                node.id = self._GetUniqueName(node.id, [n.id for n in self._nodes])

                with self.controller.group_action():
                    nodei = self.controller.add_node_g(self._net_index, node)
                    fill_color = get_theme('node_fill')
                    border_color = get_theme('node_border')
                    border_width = get_theme('node_border_width')
                    self.controller.set_node_fill_rgb(self._net_index, nodei, fill_color)
                    self.controller.set_node_fill_alpha(self._net_index, nodei, fill_color.Alpha())
                    self.controller.set_node_border_rgb(self._net_index, nodei, border_color)
                    self.controller.set_node_border_alpha(
                        self._net_index, nodei, border_color.Alpha())
                    self.controller.set_node_border_width(self._net_index, nodei, border_width)

                index = self.controller.get_node_index(self._net_index, node.id)
                with self._SelectGroupEvent():
                    self.sel_nodes_idx.set_item({index})
                    self.sel_reactions_idx.set_item(set())
                    self.sel_compartments_idx.set_item(set())
            elif cstate.input_mode == InputMode.ADD_COMPARTMENTS:
                self._drag_selecting = True
                self._drag_select_start = logical_pos
                self._drag_rect = Rect(self._drag_select_start, Vec2())
                self.drag_sel_nodes_idx = set()
            elif cstate.input_mode == InputMode.ZOOM:
                zooming_in = not wx.GetKeyState(wx.WXK_SHIFT)
                self.IncrementZoom(zooming_in, Vec2(device_pos))

        finally:
            if self.dragged_element is not None:
                self._RedrawDynamicToBuffer()
            else:
                self.FullRedraw()
            evt.Skip()
            wx.CallAfter(self.SetFocus)

    def _FloatNodes(self):
        """Helper that temporarily resets the layer of the nodes being dragged.
        """
        if self._nodes_floating:
            return
        self._nodes_floating = True
        # Only "float" if only nodes (and possibly reactions) are selected.
        if len(self.sel_compartments_idx) != 0:
            return
        node_elements: List[NodeElement] = list()

        for elt in self._node_elements:
            elt = cast(NodeElement, elt)
            if elt.node.index in self.sel_nodes_idx:
                node_elements.append(elt)

        for elt in node_elements:
            self.ResetLayer(elt, self.DRAGGED_NODE_LAYER)

    def _UnfloatNodes(self):
        # Only "float" if only nodes (and possibly reactions) are selected.
        if len(self.sel_compartments_idx) != 0:
            return

        for elt in self._node_elements:
            self.ResetLayer(elt, self.NODE_LAYER)

    def OnLeftUp(self, evt):
        try:
            self._EndDrag(evt)
            # self._UnfloatNodes()
            self._nodes_floating = False
        finally:
            self.FullRedraw()
            evt.Skip()

    def OnRightUp(self, evt):
        """Right mouse button up event handler.

        Note that the handling of the right click up event is determined by the canvas rather
        than by the individual elements.
        """
        device_pos = Vec2(evt.GetPosition())
        logical_pos = Vec2(self.CalcUnscrolledPosition(evt.GetPosition())) / cstate.scale

        overlay = self._InWhichOverlay(device_pos)
        if overlay is not None:
            return

        node_el: Optional[NodeElement] = None
        reaction_el: Optional[ReactionElement] = None
        comp_el: Optional[CompartmentElt] = None
        for el in self._ElementsHighToLow():
            if not el.enabled:
                continue
            if el.pos_inside(logical_pos):
                if isinstance(el, NodeElement):
                    node_el = cast(NodeElement, el)
                    break
                elif isinstance(el, ReactionElement):
                    reaction_el = cast(ReactionElement, el)
                    break
                elif isinstance(el, CompartmentElt):
                    comp_el = cast(CompartmentElt, el)
                    break

        on_selected = False  # Whether clicked on a selected element.
        selected_nodes: Set[int] = set()
        selected_reactions: Set[int] = set()
        selected_comps: Set[int] = set()
        if node_el is not None:
            if node_el.node.index in self.sel_nodes_idx:
                on_selected = True
            else:
                selected_nodes.add(node_el.node.index)
        elif reaction_el is not None:
            if reaction_el.reaction.index in self.sel_reactions_idx:
                on_selected = True
            else:
                selected_reactions.add(reaction_el.reaction.index)
        elif comp_el is not None:
            if comp_el.compartment.index in self.sel_compartments_idx:
                on_selected = True
            else:
                selected_comps.add(comp_el.compartment.index)

        if on_selected:
            # If right-clicked on selected element, then don't need to update anything, but only
            # need to populate right-clicked element lists.
            selected_nodes = self.sel_nodes_idx.item_copy()
            selected_reactions = self.sel_reactions_idx.item_copy()
            selected_comps = self.sel_compartments_idx.item_copy()
        else:
            # If right-clicked on something not selected, update selected indices.
            cur_selected = (len(self.sel_nodes_idx) + len(self.sel_reactions_idx) +
                            len(self.sel_compartments_idx))
            new_selected = len(selected_nodes) + len(selected_reactions) + len(selected_comps)
            # If nothing is selected before or after, don't update anything
            if cur_selected != 0 or new_selected != 0:
                with self._SelectGroupEvent():
                    self.sel_nodes_idx.set_item(selected_nodes)
                    self.sel_reactions_idx.set_item(selected_reactions)
                    self.sel_compartments_idx.set_item(selected_comps)

        # Whether clicked on something?
        total_selected = len(selected_nodes) + len(selected_reactions) + len(selected_comps)
        menu = wx.Menu()

        # def add_item(menu: wx.Menu, menu_name, callback):
        #    qmi = wx.MenuItem(menu, -1, menu_name)
        #    #qmi.SetBitmap(wx.Bitmap('exit.png'))
        #    id_ = menu.Append(qmi) # (-1, menu_name).Id
        #    menu.Bind(wx.EVT_MENU, lambda _: callback(), id=id_)

        def add_item(menu: wx.Menu, menu_name: str, callback, image_name: str = None):
            item = menu.Append(-1, menu_name)

            if image_name != None:
                item.SetBitmap(wx.Bitmap(resource_path(image_name)))
            menu.Bind(wx.EVT_MENU, lambda _: callback(), id=item.Id)

        if total_selected != 0:
            add_item(menu, 'Delete', self.DeleteSelectedItems)

        if len(selected_nodes) != 0:
            menu.AppendSeparator()
            add_item(menu, 'Create Alias', lambda: self.CreateAliases(self.sel_nodes))
            if len(self.sel_nodes) == 1 and len(self.node_to_rxn[self.sel_nodes[0].index]) > 1:
                add_item(menu, 'Split on Reactions',
                         lambda: self.SplitAliasesOnReactions(self.sel_nodes[0]))
            # Only allow align when the none of the nodes are in a compartment. This prevents
            # nodes inside a compartment being arranged outside.
            if not any(node.comp_idx != -1 for node in self.sel_nodes):
                # Only allow alignment if all selected nodes are in the same compartment
                # Add alignment options

                menu.AppendSeparator()
                align_menu = wx.Menu()
                add_item(align_menu, 'Align Left',
                         lambda: self.AlignSelectedNodes(Alignment.LEFT),
                         'alignLeft_XP.png')
                add_item(align_menu, 'Align Right',
                         lambda: self.AlignSelectedNodes(Alignment.RIGHT),
                         'alignRight_XP.png')
                add_item(align_menu, 'Align Center',
                         lambda: self.AlignSelectedNodes(Alignment.CENTER),
                         'alignHorizCenter_XP.png')
                align_menu.AppendSeparator()
                add_item(align_menu, 'Align Top',
                         lambda: self.AlignSelectedNodes(Alignment.TOP),
                         'alignTop_XP.png')
                add_item(align_menu, 'Align Bottom',
                         lambda: self.AlignSelectedNodes(Alignment.BOTTOM),
                         'AlignBottom_XP.png')
                add_item(align_menu, 'Align Middle',
                         lambda: self.AlignSelectedNodes(Alignment.MIDDLE),
                         'alignVertCenter_XP.png')
                align_menu.AppendSeparator()
                add_item(align_menu, 'Grid',
                         lambda: self.AlignSelectedNodes(Alignment.GRID),
                         'alignOnGrid_XP.png')
                align_menu.AppendSeparator()
                add_item(align_menu, 'Arrange Horizontally',
                         lambda: self.AlignSelectedNodes(Alignment.HORIZONTAL),
                         'alignHorizEqually_XP.png')
                add_item(align_menu, 'Arrange Vertically',
                         lambda: self.AlignSelectedNodes(Alignment.VERTICAL),
                         'alignVertEqually_XP.png')
                menu.AppendSubMenu(align_menu, text='Align...')

        # Must refresh before the context menu is displayed, otherwise the refresh won't occur
        self.Refresh()
        self.PopupMenu(menu)
        menu.Destroy()

    def CreateAliases(self, nodes: List[Node]):
        new_indices = set()
        with self.controller.group_action():
            for node in nodes:
                alias_pos = node.position + Vec2.repeat(20)
                if node.comp_idx >= 0:
                    comp = self.comp_idx_map[node.comp_idx]
                    alias_pos = clamp_rect_pos(Rect(alias_pos, node.size), comp.rect)

                new_idx = self.controller.add_alias_node(self.net_index, node.index,
                                                         alias_pos,
                                                         node.size)
                new_indices.add(new_idx)
        self.sel_nodes_idx.set_item(new_indices)

    def SplitAliasesOnReactions(self, node: Node):
        rea_els = [re for re in self._reaction_elements if re.reaction.index in self.node_to_rxn[node.index]]
        with self.controller.group_action():
            # exclude the first reaction
            for rea_el in rea_els[1:]:
                reaction = rea_el.reaction
                alias_pos = node.position * 0.8 + rea_el.bezier.real_center * 0.2
                if node.comp_idx >= 0:
                    comp = self.comp_idx_map[node.comp_idx]
                    alias_pos = clamp_rect_pos(Rect(alias_pos, node.size), comp.rect)

                # move node position slightly toward the position of the reaction
                self.controller.alias_for_reaction(self.net_index, reaction.index, node.index,
                                                   alias_pos, node.size)

    def GetBoundingRect(self) -> Optional[Rect]:
        """Get the bounding rectangle of all nodes, reactions, and compartments.

        Returns None if there are no nodes, reactions, or compartments.
        """
        rects = list()
        for el in self._node_elements:
            rects.append(el.bounding_rect())
        for el in self._reaction_elements:
            rects.append(el.bounding_rect())
        for el in self._compartment_elements:
            rects.append(el.bounding_rect())

        if len(rects) != 0:
            return get_bounding_rect(rects)
        else:
            return None

    def findMinX(self, nodes: List[Node]):
        '''
        Find the left-most node's x position
        Args:
            self
            l: the list of indices of the selected nodes
        '''
        return min(n.position.x for n in nodes)

    def findMaxX(self, nodes: List[Node]):
        '''
        Find the right-most node's x position
        Args:
            self
            l: the list of indices of the selected nodes
        '''
        return max(n.position.x for n in nodes)

    def findMinY(self, nodes: List[Node]):
        '''
        Find the left-most node's x position
        Args:
            self
            l: the list of indices of the selected nodes
        '''
        return min(n.position.y for n in nodes)

    def findMaxY(self, nodes: List[Node]):
        '''
        Find the right-most node's x position
        Args:
            self
            l: the list of indices of the selected nodes
        '''
        return max(n.position.y for n in nodes)


    def _DefaultHandlePositions(self, rea_el: ReactionElement):
        center = rea_el.bezier.real_center
        reactants = [self.node_idx_map[i] for i in rea_el.reaction.sources]
        products = [self.node_idx_map[i] for i in rea_el.reaction.targets]
        return default_handle_positions(center, reactants, products)

    def setDefaultHandles(self):
        with self.controller.group_action():
            for r_el in self._reaction_elements:
                r = r_el.reaction
                handles = self._DefaultHandlePositions(r_el)  # centroid, sources, target
                sources = r.sources
                targets = r.targets
                self.controller.set_center_handle(0, r.index, handles[0])
                count = 1
                for s in sources:
                    self.controller.set_src_node_handle(0, r.index, s, handles[count])
                    count += 1
                for t in targets:
                    self.controller.set_dest_node_handle(0, r.index, t, handles[count])
                    count += 1

    def AlignSelectedNodes(self, alignment: Alignment):
        """Align the selected nodes. Should be called only when *only* nodes are selected."""
        # The selected nodes are self.sel_nodes
        # To access a file in the resources folder, use
        # Jin_edit:refer to plugins/arrange.py

        sel_nodes = self.sel_nodes
        if alignment == Alignment.LEFT:
            # Align selected nodes to the left-most node's x position
            with self.controller.group_action():
                xpos = self.findMinX(sel_nodes)
                for n in sel_nodes:
                    newPos = Vec2(xpos, n.position.y)
                    self.controller.move_node(self.net_index, n.index, newPos)
            self.setDefaultHandles()

        elif alignment == Alignment.RIGHT:
            '''
            Align selected nodes to the right-most node's x position
            '''
            with self.controller.group_action():
                xpos = self.findMaxX(sel_nodes)
                for n in self.sel_nodes:
                    newPos = Vec2(xpos, n.position.y)
                    self.controller.move_node(self.net_index, n.index, newPos)
            self.setDefaultHandles()

        elif alignment == Alignment.CENTER:
            '''
            Align selected nodes to the relative center of the x positions of the nodes
            '''
            with self.controller.group_action():
                xMin = self.findMinX(sel_nodes)
                xMax = self.findMaxX(sel_nodes)
                xpos = math.floor((xMax + xMin)/2)
                for n in sel_nodes:
                    newPos = Vec2(xpos, n.position.y)
                    self.controller.move_node(self.net_index, n.index, newPos)
            self.setDefaultHandles()

        elif alignment == Alignment.TOP:
            with self.controller.group_action():
                ypos = self.findMinY(sel_nodes)
                for n in self.sel_nodes:
                    newPos = Vec2(n.position.x, ypos)
                    self.controller.move_node(self.net_index, n.index, newPos)
            self.setDefaultHandles()

        elif alignment == Alignment.BOTTOM:
            with self.controller.group_action():
                ypos = self.findMaxY(sel_nodes)
                for n in self.sel_nodes:
                    newPos = Vec2(n.position.x, ypos)
                    self.controller.move_node(self.net_index, n.index, newPos)
            self.setDefaultHandles()

        elif alignment == Alignment.MIDDLE:
            # Align selected nodes to the relative center of the x positions of the nodes
            with self.controller.group_action():
                yMin = self.findMinY(sel_nodes)
                yMax = self.findMaxY(sel_nodes)
                ypos = math.floor((yMax + yMin)/2)
                for n in sel_nodes:
                    newPos = Vec2(n.position.x, ypos)
                    self.controller.move_node(0, n.index, newPos)
            self.setDefaultHandles()

        elif alignment == Alignment.GRID:
            '''
            Align selected nodes in a net grid manner
            '''
            with self.controller.group_action():
                x = 40
                y = 40
                count = 1
                for n in sel_nodes:
                    self.controller.move_node(0, n.index, Vec2(x, y))
                    x = x + 130
                    if count % 5 == 0:
                        y = y + 130
                        x = 40
                    count = count + 1
            self.setDefaultHandles()

        elif alignment == Alignment.HORIZONTAL:

            # Sort the selected nodes in x position ascending order
            nodes = sorted(sel_nodes, key=lambda x: x.position.x)

            # find the average distance beteeen the selected nodes
            averageDistance = 0.0
            for count in range(1, len(nodes)):
                node2 = nodes[count-1]
                node1 = nodes[count]
                averageDistance += (node1.position.x + node1.size.x) - node2.position.x
            averageDistance = averageDistance / len(nodes)

            with self.controller.group_action():
                # x = Position of left most node
                x = nodes[0].position.x
                # Arrange nodes with equal distance between them
                for count in range(len(nodes)):
                    newPos = Vec2(x, nodes[count].position.y)
                    self.controller.move_node(0, nodes[count].index, newPos)
                    x = x + averageDistance
            self.setDefaultHandles()

        elif alignment == Alignment.VERTICAL:

            # Sort the selected nodes in y position ascending order
            nodes = sorted(sel_nodes, key=lambda x: x.position.y)

            # find the average distance beteeen the selected nodes
            averageDistance = 0.0
            for count in range(1, len(nodes)):
                node2 = nodes[count - 1]
                node1 = nodes[count]
                averageDistance += (node1.position.y + node1.size.y) - node2.position.y
            averageDistance = averageDistance / len(nodes)

            with self.controller.group_action():
                # y = Position of top most node
                y = nodes[0].position.y
                # Arrange nodes with equal distance between them
                for count in range(len(nodes)):
                    newPos = Vec2(nodes[count].position.x, y)
                    self.controller.move_node(0, nodes[count].index, newPos)
                    y = y + averageDistance
            self.setDefaultHandles()

    # TODO improve this. we might want a special mouseLeftWindow event
    def _EndDrag(self, evt: wx.MouseEvent):
        """Send the updated node positions and sizes to the controller.

        This is called after a dragging operation has completed in OnLeftUp or OnLeaveWindow.
        """
        device_pos = Vec2(evt.GetPosition())
        overlay = self._InWhichOverlay(device_pos)

        if self._minimap.dragging:
            self._minimap.OnLeftUp(device_pos)
            # HACK once we integrate overlays (e.g. minimap) as CanvasElements, we can simply call
            # on_mouse_leave or something
            self._minimap.hovering = False
        elif self._minimap.hovering:
            self._minimap.hovering = False
        elif self._drag_selecting:
            self._drag_selecting = False
            if cstate.input_mode == InputMode.SELECT:
                self.sel_nodes_idx.union(self.drag_sel_nodes_idx)
                self.sel_reactions_idx.union(self.drag_sel_rxns_idx)
                self.sel_compartments_idx.union(self.drag_sel_comps_idx)
                self.drag_sel_nodes_idx = set()
                self.drag_sel_rxns_idx = set()
                self.drag_sel_comps_idx = set()
            elif cstate.input_mode == InputMode.ADD_COMPARTMENTS:
                id = self._GetUniqueName('c', [c.id for c in self._compartments])

                size = self._drag_rect.size
                # make sure the compartment is at least of some size
                adj_size = Vec2(max(size.x, get_setting('min_comp_width')),
                                max(size.y, get_setting('min_comp_height')))
                # compute position
                size_diff = adj_size - self._drag_rect.size
                # center position if drag_rect size has been adjusted
                pos = self._drag_rect.position - size_diff / 2

                comp = Compartment(id,
                                   index=self.comp_index,
                                   net_index=self.net_index,
                                   nodes=list(),
                                   volume=1,
                                   position=pos,
                                   size=adj_size,
                                   fill=get_theme('comp_fill'),
                                   border=get_theme('comp_border'),
                                   border_width=get_theme('comp_border_width'),
                                   )
                # clip position
                comp.position = clamp_rect_pos(comp.rect, Rect(Vec2(), self.realsize), BOUNDS_EPS)
                self.controller.add_compartment_g(self.net_index, comp)
        elif cstate.input_mode == InputMode.SELECT:
            # perform left_up on dragged_element if it exists, or just find the node under the
            # cursor
            logical_pos = self.CalcScrolledPositionFloat(device_pos) / cstate.scale
            if self.dragged_element is not None:
                self.dragged_element.on_left_up(logical_pos)
                self.dragged_element = None
            elif self.hovered_element is not None:
                self.hovered_element.on_mouse_leave(logical_pos)
                self.hovered_element = None
            elif evt.LeftIsDown():
                for el in self._ElementsHighToLow():
                    if not el.enabled:
                        continue
                    if el.pos_inside(logical_pos) and el.on_left_up(logical_pos):
                        return

        if overlay is not None:
            overlay.OnLeftUp(device_pos)

    def CalcScrolledPositionFloat(self, pos: Vec2) -> Vec2:
        """Convert logical position to scrolled (device) position, retaining floating point.

        self.CalcScrolledPosition() converts the input floats to ints. This is needed if better
        accuracy is needed.
        """
        return Vec2(self.CalcScrolledPosition(wx.Point(0, 0))) + pos

    def CalcUnscrolledPositionFloat(self, pos: Vec2) -> Vec2:
        return Vec2(self.CalcUnscrolledPosition(wx.Point(0, 0))) + pos

    def OnMotion(self, evt):
        now = time.time()
        if now - self.last_motion < 0.01:
            return
        self.last_motion = now

        # Update cursor status text here
        if self._cursor_logical_pos is not None:
            rounded = self._cursor_logical_pos.map(lambda e: round(e, 2))
            status_text = repr(rounded)
            self._SetStatusText('cursor', status_text)

        assert isinstance(evt, wx.MouseEvent)
        redraw = False
        try:
            device_pos = Vec2(evt.GetPosition())
            logical_pos = Vec2(self.CalcUnscrolledPosition(evt.GetPosition())) / cstate.scale
            self._cursor_logical_pos = logical_pos
            rxn_radius = get_theme('reaction_radius')

            if self._drag_selecting:
                # assert evt.leftIsDown
                topleft = Vec2(min(logical_pos.x, self._drag_select_start.x),
                               min(logical_pos.y, self._drag_select_start.y))
                botright = Vec2(max(logical_pos.x, self._drag_select_start.x),
                                max(logical_pos.y, self._drag_select_start.y))
                self._drag_rect = Rect(topleft, botright - topleft)
                if cstate.input_mode == InputMode.SELECT:
                    selected_nodes = [n for n in self._nodes
                                      if rects_overlap(n.s_rect, self._drag_rect)]
                    selected_comps = [c for c in self._compartments
                                      if rects_overlap(c.rect, self._drag_rect)]
                    selected_rxns = [re.reaction for re in self._reaction_elements
                                     if rects_overlap(circle_bounds(
                                         re.bezier.real_center, rxn_radius),
                                         self._drag_rect)]
                    new_drag_sel_nodes_idx = set(n.index for n in selected_nodes)
                    new_drag_sel_rxns_idx = set(r.index for r in selected_rxns)
                    new_drag_sel_comps_idx = set(c.index for c in selected_comps)

                    reactions_updated = new_drag_sel_rxns_idx != self.drag_sel_rxns_idx
                    if (new_drag_sel_nodes_idx != self.drag_sel_nodes_idx or
                            reactions_updated or
                            new_drag_sel_comps_idx != self.drag_sel_comps_idx):
                        self.drag_sel_nodes_idx = new_drag_sel_nodes_idx
                        self.drag_sel_rxns_idx = new_drag_sel_rxns_idx
                        self.drag_sel_comps_idx = new_drag_sel_comps_idx
                        self._UpdateSelectedLists()

                    if reactions_updated:
                        # If drag selected reactions changed, then update reaction selection state.
                        all_selected = self.drag_sel_rxns_idx | self.sel_reactions_idx.item_copy()
                        for rel in self._reaction_elements:
                            rel.selected = rel.reaction.index in all_selected
                elif cstate.input_mode == InputMode.ADD_COMPARTMENTS:
                    pass
                redraw = True
                return

            # dragging takes priority here
            if evt.leftIsDown:  # dragging
                if self.dragged_element is not None:
                    rel_pos = logical_pos - self._last_drag_pos
                    if self.dragged_element.on_mouse_drag(logical_pos, rel_pos):
                        redraw = True
                    self._last_drag_pos = logical_pos
                    # If redrawing, i.e. dragged element moved, return immediately. Otherwise
                    # we need to check if the mouse is still inside the dragged element.
                    # The early return is for performance.
                    if redraw:
                        return
                elif self._minimap.dragging:
                    self._minimap.OnMotion(device_pos, evt.LeftIsDown())
                    redraw = True
                    return
            else:
                overlay = self._InWhichOverlay(device_pos)
                if overlay is not None:
                    overlay.OnMotion(device_pos, evt.LeftIsDown())
                    overlay.hovering = True
                    redraw = True

                # un-hover all other overlays TODO keep track of the currently hovering overlay
                for ol in self._overlays:
                    if ol is not overlay and ol.hovering:
                        ol.hovering = False
                        redraw = True

            # Likely hovering on something else
            hovered: Optional[CanvasElement] = None
            for el in self._ElementsHighToLow():
                if not el.enabled:
                    continue
                if el.pos_inside(logical_pos):
                    hovered = el
                    break

            if cstate.input_mode == InputMode.ADD_NODES and (
                    isinstance(self.hovered_element, CompartmentElt)
                    or isinstance(hovered, CompartmentElt)):
                # set redraw to True whenever input mode is ADD_NODES and mouse enters, exits,
                # or moves in a compartment. This is for updating the hightlight of the compartment.
                # (see CompartmentElt.on_paint).
                redraw = True

            if hovered is not None and hovered is self.hovered_element:
                moved = self.hovered_element.on_mouse_move(logical_pos)
                redraw = redraw or moved
            else:
                if self.hovered_element is not None:
                    redraw = redraw or self.hovered_element.on_mouse_leave(logical_pos)
                if hovered is not None:
                    redraw = redraw or hovered.on_mouse_enter(logical_pos)
                self.hovered_element = hovered
        finally:
            if redraw:
                self.LazyRefresh()
            evt.Skip()

    def FullRedraw(self):
        '''Function to signal that the entire canvas needs to be redrawn.'''
        self._static_bitmap = None
        self._dirty = True
        self.LazyRefresh()

    def LazyRefresh(self) -> bool:
        now = int(time.time() * 1000)
        diff = now - self._last_refresh
        if diff < self.MILLIS_PER_REFRESH:
            def callback(then_time):
                if then_time == self._last_refresh:
                    # no refreshes since then; do the refresh now
                    self._last_refresh = then_time
                    self.Refresh()

            wx.CallLater(self.MILLIS_PER_REFRESH, lambda: callback(now))
            return False
        else:
            self._last_refresh = now
            self.Refresh()
            return True

    def RedrawModelElements(self):
        '''Redraw the 'model', i.e. non-widget, elements, such as nodes and reactions. This is used
        for optimizing drawing.
        '''
        pass

    def OnPaint(self, evt):
        self._accum_frames += 1
        now = time.time() * 1000
        diff = now - self._last_fps_update
        if diff >= 1000:
            self._last_fps_update = int(now)
            fps = int(self._accum_frames / diff * 1000)
            self._SetStatusText('fps', 'refreshes/sec: {}'.format(int(fps)))
            self._accum_frames = 0
        self.SetOverlayPositions()  # have to do this here to prevent jitters

        dc = wx.PaintDC(self)

        # transform for drawing to scrolled coordinates
        self.DoPrepareDC(dc)

        # Draw everything
        gc = wx.GraphicsContext.Create(dc)
        assert gc is not None

        if self._static_bitmap is None:
            # draw the whole thing
            self._RedrawDynamicToBuffer()

        wpos = Vec2(self.CalcUnscrolledPosition(0, 0))
        wsize = Vec2(self.GetSize())

        draw_rect(
            gc,
            Rect(wpos, wsize),
            fill=get_theme('canvas_outside_bg'),
        )

        subpos = wpos
        # sometimes the subbitmap might overflow. need to restrict its size to be within the canvas
        subsize = Vec2(min(self.realsize.x - subpos.x, wsize.x), min(self.realsize.y - subpos.y, wsize.y))
        bitmap = self._static_bitmap.GetSubBitmap(wx.Rect(int(subpos.x), int(subpos.y), int(subsize.x), int(subsize.y)))
        gc.DrawBitmap(bitmap, wpos.x, wpos.y, bitmap.GetWidth(), bitmap.GetHeight())
        # draw dynamic elements
        gc.PushState()
        gc.Scale(cstate.scale, cstate.scale)
        for elt in self._ElementsLowToHigh():
            if elt in self._dynamic_elements and elt.enabled:
                # draw to static buffer
                elt.on_paint(gc)
        self.DrawVisualCuesToGC(gc)
        gc.PopState()

        # Draw minimap
        self._minimap.DoPaint(gc)

        post_event(DidPaintCanvasEvent(gc))

    def DrawActiveRectToImage(self):
        """Draw to image only the active rectangle -- bounding rect of nodes, reactions, & compartments
        """
        bounding_rect = self.GetBoundingRect()
        if bounding_rect is None:
            return None

        bounding_rect = padded_rect(bounding_rect, padding=50)
        #bounding_rect = wx.Rect(*bounding_rect.position, *bounding_rect.size)
        pos_list = list(bounding_rect.position)
        pos_list = [int(pos_item) for pos_item in pos_list]
        size_list = list(bounding_rect.size)
        size_list = [int(size_item) for size_item in size_list]
        bounding_rect = wx.Rect(*pos_list, *size_list)
        bounding_rect.Intersect(wx.Rect(0, 0, *self.realsize))

        bmp = wx.Bitmap(*self.realsize)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        gc = wx.GraphicsContext.Create(dc)
        self.DrawBackgroundToGC(gc)
        self.DrawModelToGC(gc)
        img = bmp.ConvertToImage()
        ret = img.GetSubImage(bounding_rect)
        return ret

    def DrawBackgroundToGC(self, gc):
        # # Draw gray background
        # draw_rect(
        #     gc,
        #     Rect(Vec2(0, 0), self.realsize + Vec2(10, 10)),
        #     fill=get_theme('canvas_outside_bg'),
        # )
        # Draw background TODO move this before gc.Scale()
        draw_rect(
            gc,
            Rect(Vec2(0, 0), self.realsize),
            fill=get_theme('canvas_bg'),
        )

    def DrawModelToGC(self, gc: wx.GraphicsContext):
        for elt in self._model_elements:
            if elt.enabled:
                elt.on_paint(gc)

    def _GetReactionWidgets(self, rxn_elt: ReactionElement) -> Iterable[CanvasElement]:
        return chain(rxn_elt.bhandles, [rxn_elt.center_el])

    def _GetDynamicElements(self) -> Set[CanvasElement]:
        '''Get the set of elements that will change, as self.dragged_element is dragged.
        '''
        if self.dragged_element is None:
            return set()
        elts = list()
        if isinstance(self.dragged_element, SelectBox):
            elts.append(self.dragged_element)
            # all the nodes that move along with the select box
            node_idc = set(chain([n.index for n in self.dragged_element.nodes],
                [n.index for n in self.dragged_element.peripheral_nodes]))
            rxn_idc = set().union(*(self.node_to_rxn[ni] for ni in node_idc))
            comp_idc = set(c.index for c in self.dragged_element.compartments)

            elts += [cast(CanvasElement, x) for x in self._node_elements if x.node.index in node_idc]
            elts += [cast(CanvasElement, x) for x in self._compartment_elements if x.compartment.index in comp_idc]

            # add reactions
            rxn_elts = list(x for x in self._reaction_elements if x.reaction.index in rxn_idc)
            for rxn_elt in rxn_elts:
                elts.append(rxn_elt)
                elts += self._GetReactionWidgets(rxn_elt)

        elif isinstance(self.dragged_element, ReactionCenter):
            rxn_elt = self.dragged_element.parent
            elts.append(rxn_elt)
            elts += self._GetReactionWidgets(rxn_elt)
        elif isinstance(self.dragged_element, BezierHandle):
            ri = self.dragged_element.reaction.index
            rxn_elts = [x for x in self._reaction_elements if x.reaction.index == ri]
            assert(len(rxn_elts) == 1)

            rxn_elt = rxn_elts[0]
            elts.append(rxn_elt)
            elts += self._GetReactionWidgets(rxn_elt)
            # TODO add
            # if isinstance(self.dragged_element, ReactionElement):
            #     rxn_elt = self.dragged_element
            # elif isinstance(self.dragged_element, ReactionCenter):
            #     rxn_elt = self.dragged_element.parent
            # elif isinstance(self.dragged_element, BezierHandle):
            #     # TODO add twin
            #     rxn_elt = self.dragged_element.reaction

            # if rxn_elt is not None:
            #     elts.append(rxn_elt)
            #     elts += rxn_elt.bhandles
            #     elts.append(rxn_elt.center_el)

        return set(elts)

    def _RedrawDynamicToBuffer(self):
        self._dynamic_elements = self._GetDynamicElements()
        # No dynamic elements; simply redraw everything by not populating _static_bitmap

        temp_bitmap = wx.Bitmap(*self.realsize)
        self._dirty = False
        dc = wx.MemoryDC()
        dc.SelectObject(temp_bitmap)
        gc: wx.GraphicsContext = wx.GraphicsContext.Create(dc)

        self.DrawBackgroundToGC(gc)
        gc.PushState()
        gc.Scale(cstate.scale, cstate.scale)
        for elt in self._ElementsLowToHigh():
            if elt not in self._dynamic_elements and elt.enabled:
                # draw to static buffer
                elt.on_paint(gc)
        gc.PopState()

        self._static_bitmap = temp_bitmap

    def _DrawCompartmentHighlight(self, gc: wx.GraphicsContext):
        # TODO this is not model
        within_comp = None
        if cstate.input_mode == InputMode.ADD_NODES and self._cursor_logical_pos is not None:
            size = Vec2(get_theme('node_width'), get_theme('node_height'))
            pos = self._cursor_logical_pos - size/2
            within_comp = self.RectInWhichCompartment(Rect(pos, size))
        elif self._select_box.special_mode == SelectBox.SMode.NODES_IN_ONE and self.dragged_element is not None:
            within_comp = self.InWhichCompartment(self._select_box.nodes)

        if within_comp is None or within_comp == -1:
            return

        for elt in self._compartment_elements:
            if elt.compartment.index == within_comp:
                elt.highlight_paint(gc)
                return
        assert False, 'Should not reach here'


    def _DrawDragSelectionRect(self, gc):
        if self._drag_selecting:
            fill: wx.Colour
            border: Optional[wx.Colour]
            bwidth: int
            if cstate.input_mode == InputMode.SELECT:
                fill = get_theme('drag_fill')
                border = get_theme('drag_border')
                bwidth = get_theme('drag_border_width')
                corner_radius = 0
            elif cstate.input_mode == InputMode.ADD_COMPARTMENTS:
                fill = opacity_mul(get_theme('comp_fill'), 0.3)
                border = opacity_mul(get_theme('comp_border'), 0.3)
                bwidth = get_theme('comp_border_width')
                corner_radius = get_theme('comp_corner_radius')
            else:
                assert False, "Should not be _drag_selecting in any other input mode."

            if bwidth == 0:
                border = None

            draw_rect(
                gc,
                self._drag_rect,
                fill=fill,
                border=border,
                border_width=bwidth,
                corner_radius=corner_radius,
            )

    def DrawVisualCuesToGC(self, gc):
        '''Visual cues include reactant/product outlines, drag-selection rectangle, and
        compartment highlight.'''
        # TODO Put this in SelectionChanged
        for el in self._ElementsLowToHigh():
            if not el.enabled:
                continue
            el.on_paint_cue(gc)

        self._DrawCompartmentHighlight(gc)

        sel_rects = ([n.rect for n in self.sel_nodes] +
                     [c.rect for c in self.sel_comps])

        # If we are not drag-selecting, don't draw selection outlines if there is only one rect
        # selected (for aesthetics); but do draw outlines if drawing_drag is True (as
        # documented in _UpdateSelectedLists())
        if len(sel_rects) > 1 or self.drawing_drag:
            for rect in sel_rects:
                rect = rect.aligned()
                # Draw selection outlines
                rect = padded_rect(rect, get_theme('select_outline_padding'))
                # draw rect
                draw_rect(gc, rect, border=get_theme('handle_color'),
                          border_width=get_theme('select_outline_width'),
                          corner_radius=0)

        # Draw reactant and product marker outlines
        def draw_reaction_outline(node: Node, color: wx.Colour, padding: int):
            draw_rect(
                gc,
                padded_rect(node.s_rect.aligned(), padding),
                fill=None,
                border=color,
                border_width=max(even_round(get_theme('react_node_border_width')), 2),
                border_style=wx.PENSTYLE_LONG_DASH,
            )

        reactants = get_nodes_by_idx(self._nodes, self._reactant_idx)
        for node in reactants:
            draw_reaction_outline(node, get_theme('reactant_border'),
                                  get_theme('react_node_padding'))

        products = get_nodes_by_idx(self._nodes, self._product_idx)
        for node in products:
            pad = get_theme('react_node_border_width') + \
                3 if node.index in self._reactant_idx else 0
            draw_reaction_outline(node, get_theme('product_border'),
                                  pad + get_theme('react_node_padding'))

        # Draw drag-selection rect
        self._DrawDragSelectionRect(gc)

    def ResetLayer(self, elt: CanvasElement, layers: Layer):
        if elt in self._model_elements:
            self._model_elements.remove(elt)
            elt.set_layers(layers)
            self._model_elements.add(elt)
        elif elt in self._widget_elements:
            self._widget_elements.remove(elt)
            elt.set_layers(layers)
            self._widget_elements.add(elt)

    def GetSelectedNodes(self, copy=False) -> List[Node]:
        """Get the list of selected nodes using self.sel_nodes_idx."""
        if copy:
            return [copy.copy(n) for n in self._nodes if self.sel_nodes_idx.contains(n.index)]
        else:
            return [n for n in self._nodes if self.sel_nodes_idx.contains(n.index)]

    def OnScroll(self, evt):
        # Need to use wx.CallAfter() to ensure the scroll event is finished before we update the
        # position of the dragged node
        evt.Skip()
        self.SetOverlayPositions()
        self.LazyRefresh()
        # self.FullRedraw()

    def OnMouseWheel(self, evt):
        rot = evt.GetWheelRotation()
        if wx.GetKeyState(wx.WXK_CONTROL):
            # zooming in or out
            self.IncrementZoom(rot > 0, Vec2(evt.GetPosition()))
        else:
            # dispatch a horizontal scroll event in this case
            if evt.GetWheelAxis() == wx.MOUSE_WHEEL_VERTICAL and \
                    wx.GetKeyState(wx.WXK_SHIFT):
                evt.SetWheelAxis(
                    wx.MOUSE_WHEEL_HORIZONTAL)
                # need to invert rotation for more intuitive scrolling
                evt.SetWheelRotation(-rot)

            evt.Skip()

    def OnSlider(self, evt):
        level = self.zoom_slider.GetValue()
        self.SetZoomLevel(level, Vec2(self.GetSize()) / 2)

    def OnLeaveWindow(self, evt):
        try:
            self._EndDrag(evt)
        finally:
            evt.Skip()

    def OnDidCommitNodePositions(self, evt):
        """Update reaction Bezier handles after nodes are dragged."""
        evt = cast(DidCommitDragEvent, evt)
        if isinstance(evt.source, SelectBox):
            for elt in self._reaction_elements:
                elt.commit_node_pos()

    def _ElementsHighToLow(self) -> Iterable[CanvasElement]:
        return reversed(self._model_elements + self._widget_elements)

    def _ElementsLowToHigh(self) -> Iterable[CanvasElement]:
        return chain(self._model_elements, self._widget_elements)

    @contextmanager
    def _SelectGroupEvent(self):
        """Context for selection event group. See docs for in_selection_group for details."""
        self._in_selection_group = True
        yield
        self._in_selection_group = False
        if self._selection_dirty:
            self._SelectionChanged()
            self._selection_dirty = False

    def _UpdateSelectedLists(self):
        """Helper that updates the selected nodes, etc. using the selected indices.

        Should be called when there is an update to the indices.
        """
        sel_node_idx = self.sel_nodes_idx.item_copy()
        sel_rxn_idx = self.sel_reactions_idx.item_copy()
        sel_comp_idx = self.sel_compartments_idx.item_copy()
        orig_count = len(sel_node_idx) + len(sel_comp_idx) + len(sel_rxn_idx)
        self.drawing_drag = False
        if self._drag_selecting:
            sel_node_idx |= self.drag_sel_nodes_idx
            sel_rxn_idx |= self.drag_sel_rxns_idx
            sel_comp_idx |= self.drag_sel_comps_idx
            # Flag that indicates whether there are nodes/comps not selected but within
            # the drag-selection rectangle
            if len(sel_node_idx) + len(sel_rxn_idx) + len(sel_comp_idx) != orig_count:
                self.drawing_drag = True

        self.sel_nodes = [n for n in self._nodes if n.index in sel_node_idx]
        self.sel_reactions = [r for r in self._reactions if r.index in sel_rxn_idx]
        self.sel_comps = [c for c in self._compartments if c.index in sel_comp_idx]

    def _SelectionChanged(self):
        """Callback passed to observer for when the node/reaction selection has changed."""
        if self._in_selection_group:
            self._selection_dirty = True
            return
        node_idx = self.sel_nodes_idx.item_copy()
        rxn_idx = self.sel_reactions_idx.item_copy()
        comp_idx = self.sel_compartments_idx.item_copy()
        # Directly update select_box here, instead of binding to a handler
        self._select_box.update([n for n in self._nodes if n.index in node_idx],
                                [c for c in self._compartments if c.index in comp_idx])
        self._UpdateSelectBoxLayer()
        for rel in self._reaction_elements:
            rel.selected = self.sel_reactions_idx.contains(rel.reaction.index)
        post_event(SelectionDidUpdateEvent(node_indices=node_idx, reaction_indices=rxn_idx,
                                           compartment_indices=comp_idx))
        cstate.input_mode = cstate.input_mode
        self._UpdateSelectedLists()

    def _UpdateSelectBoxLayer(self):
        """Helper that updates the layer of the select box, depending on what is selected."""
        if len(self._select_box.nodes) + len(self._select_box.compartments) == 0:
            return

        elements = [cast(CanvasElement, e)
                    for e in self._node_elements if e.node.index in self.sel_nodes_idx]
        elements += [cast(CompartmentElt, e) for e in self._compartment_elements if e.compartment.index in
                     self.sel_compartments_idx]
        layers = max(e.layers for e in elements)
        if isinstance(layers, int):
            layers = (Canvas.SELECT_BOX_LAYER, layers)
        else:
            layers = (Canvas.SELECT_BOX_LAYER,) + layers
        self.ResetLayer(self._select_box, layers)

    def InWhichCompartment(self, nodes: List[Node]) -> int:
        """Return which compartment the given floating rectangles are in, or -1 if not in any.

        This does not return which compartment the nodes currently are in. Rather, it assumes that
        the user is dragging the nodes (as in the nodes is floating), and tests from the highest
        compartment to the lowest, whether the nodes as a whole are considered inside that
        compartment.

        Right now, a group of nodes are considered to be inside a compartment iff all the nodes are
        entirely within in the compartment boundaries.
        """
        for el in self._ElementsHighToLow():
            if isinstance(el, CompartmentElt):
                comp = cast(CompartmentElt, el).compartment
                comp_rect = comp.rect
                if all(comp_rect.contains(n.rect) for n in nodes):
                    return comp.index
        return -1

    def RectInWhichCompartment(self, rect: Rect) -> int:
        """Same as InWhichCompartment but for a single rect"""
        for el in self._ElementsHighToLow():
            if isinstance(el, CompartmentElt):
                comp = cast(CompartmentElt, el).compartment
                comp_rect = comp.rect
                if comp_rect.contains(rect):
                    return comp.index
        return -1

    def DeleteSelectedItems(self):
        # First, get the list of reaction indices IF the currently selected reactions were deleted.
        sel_reactions_idx = self.sel_reactions_idx.item_copy()
        sel_nodes_idx = self.sel_nodes_idx.item_copy()
        rem_rxn = {r.index for r in self.reactions} - sel_reactions_idx

        # Second, confirm the selected nodes are free (i.e. not part of a reaction)
        for orig_node_idx in sel_nodes_idx:
            orig_node = self.node_idx_map[orig_node_idx]
            is_alias = orig_node.original_index != -1
            # don't need to worry about deleting aliases that are part of reactions
            if is_alias:
                continue
            aliases = [node.index for node in self.nodes if node.original_index == orig_node_idx]
            for node_idx in chain([orig_node_idx], aliases):
                if len(self.node_to_rxn[node_idx] & rem_rxn) != 0:
                    self.ShowWarningDialog(("Could not delete node '{}', as one or more reactions "
                                            "depend on it or its aliases.").format(orig_node.id))
                    self.logger.warning("Tried and failed to delete bound node '{}' with index '{}'"
                                        .format(orig_node.id, node_idx))
                    return

        with self.controller.group_action():
            sel_comp_idx = self.sel_compartments_idx.item_copy()
            for index in sel_reactions_idx:
                self.controller.delete_reaction(self._net_index, index)
            for index in sel_nodes_idx:
                self.controller.delete_node(self._net_index, index)
            for index in sel_comp_idx:
                self.controller.delete_compartment(self._net_index, index)
            post_event(DidDeleteEvent(node_indices=sel_nodes_idx, reaction_indices=sel_reactions_idx,
                                      compartment_indices=sel_comp_idx))

    def SelectAll(self):
        with self._SelectGroupEvent():
            self.sel_nodes_idx.set_item({n.index for n in self._nodes})
            self.sel_reactions_idx.set_item({r.index for r in self._reactions})
            self.sel_compartments_idx.set_item({c.index for c in self._compartments})
        self.FullRedraw()

    def SelectAllNodes(self):
        with self._SelectGroupEvent():
            self.sel_nodes_idx.set_item({n.index for n in self._nodes})
        self.FullRedraw()

    def SelectAllReactions(self):
        with self._SelectGroupEvent():
            self.sel_reactions_idx.set_item({r.index for r in self._reactions})
        self.FullRedraw()

    def ClearCurrentSelection(self):
        """Clear the current highest level of selection.

        If there are reactants or products marked, clear those. OTherwise clear selected nodes and
        reactions.
        """
        if len(self._reactant_idx) + len(self._product_idx) != 0:
            self._reactant_idx = set()
            self._product_idx = set()
            self.FullRedraw()
        else:
            with self._SelectGroupEvent():
                self.sel_nodes_idx.set_item(set())
                self.sel_reactions_idx.set_item(set())
                self.sel_compartments_idx.set_item(set())
            self.FullRedraw()

    def MarkSelectedAsReactants(self):
        self._reactant_idx = self.sel_nodes_idx.item_copy()
        # self.FullRedraw()
        self.LazyRefresh()

    def MarkSelectedAsProducts(self):
        self._product_idx = self.sel_nodes_idx.item_copy()
        # self.FullRedraw()
        self.LazyRefresh()

    def CreateReactionFromMarked(self, id='r'):
        if len(self._reactant_idx) == 0:
            self.ShowWarningDialog('Could not create reaction: no reactants selected!')
            return
        if len(self._product_idx) == 0:
            self.ShowWarningDialog('Could not create reaction: no products selected!')
            return

        if self._reactant_idx == self._product_idx:
            self.ShowWarningDialog('Could not create reaction: reactants and products are '
                                   'identical.')
            return

        id = self._GetUniqueName(id, [r.id for r in self._reactions])
        sources = get_nodes_by_idx(self._nodes, self._reactant_idx)
        targets = get_nodes_by_idx(self._nodes, self._product_idx)
        centroid = compute_centroid([n.rect for n in chain(sources, targets)])
        reaction = Reaction(
            id,
            self.net_index,
            sources=list(self._reactant_idx),
            targets=list(self._product_idx),
            fill_color=get_theme('reaction_fill'),
            line_thickness=get_theme('reaction_line_thickness'),
            rate_law='',
            center_pos=centroid,
            handle_positions=default_handle_positions(centroid, sources, targets)
        )
        reai = self.controller.add_reaction_g(self._net_index, reaction)
        self.controller.set_reaction_center(self._net_index, reai, centroid)
        self._reactant_idx.clear()
        self._product_idx.clear()
        with self._SelectGroupEvent():
            self.sel_nodes_idx.set_item(set())
            self.sel_compartments_idx.set_item(set())
            self.sel_reactions_idx.set_item(
                {self.controller.get_reaction_index(self._net_index, id)})
        self.FullRedraw()

    def CopySelected(self):
        self._copied_nodes = copy.deepcopy(self.GetSelectedNodes())
        # TODO copy reactions and compartments too

    def CutSelected(self):
        self.CopySelected()
        self.DeleteSelectedItems()

    def Paste(self):
        pasted_ids = set()
        all_ids = {n.id for n in self._nodes}

        with self.controller.group_action():
            # get unique IDs
            for node in self._copied_nodes:
                node.id = self._GetUniqueName(node.id, pasted_ids, all_ids)
                node.position += Vec2.repeat(20)
                pasted_ids.add(node.id)
                self._nodes.append(node)  # add this for the event handlers to see
                self.controller.add_node_g(self._net_index, node)
        # update selection *after* end_group(), so as to make sure the canvas is property reset
        # and updated. For example, if it is not, then the ID of some nodes may be 0 as they are
        # uninitialized.
        self.sel_nodes_idx.set_item({self.controller.get_node_index(self._net_index, id)
                                     for id in pasted_ids})

    def ShowWarningDialog(self, msg: str, caption='Warning'):
        wx.MessageBox(msg, caption, wx.OK | wx.ICON_WARNING)

    def AddPluginElement(self, net_index: int, element: CanvasElement):
        # TODO currently not accounting for net_index
        self._plugin_elements.add(element)
        self._widget_elements.add(element)

    def RemovePluginElement(self, net_index: int, element: CanvasElement):
        if element not in self._plugin_elements:
            raise ValueError("Tried to remove an element that is not on canvas.")
        self._plugin_elements.remove(element)
        self._widget_elements.remove(element)

    def GetReactionCentroids(self, net_index: int) -> Dict[int, Vec2]:
        """Helper method for ReactionForm to get access to the centroid positions.
        """
        return {r.reaction.index: r.bezier.centroid for r in self._reaction_elements}
