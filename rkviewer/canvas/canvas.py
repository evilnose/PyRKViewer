"""The interface of canvas for wxPython."""
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
from typing import Collection, DefaultDict, Dict, List, Optional, Set, Tuple, Union, cast
from commentjson.commentjson import JSONLibraryException
from marshmallow.exceptions import ValidationError
from rkplugin import api

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
    Rect,
    Vec2, circle_bounds,
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
        MIN_ZOOM_LEVEL: The minimum zoom level the user is allowed to reach. See SetZoomLevel()
            for more detail.
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
    MIN_ZOOM_LEVEL: int = -7
    MAX_ZOOM_LEVEL: int = 7
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
    reaction_map: DefaultDict[int, Set[int]]
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
    _elements: SortedKeyList
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
    reaction_idx_map: Dict[int, Reaction]  # ; Maps reaction index to reaction
    comp_idx_map: Dict[int, Compartment]  #: Maps compartment index to compartment
    sel_nodes: List[Node]  #: Current list of selected nodes; cached for performance
    sel_reactions: List[Reaction]
    sel_comps: List[Compartment]  #: Current list of selected comps; cached for performance
    drawing_drag: bool  #: See self._UpdateSelectedLists() for more details

    def __init__(self, controller: IController, zoom_slider, *args, realsize: Tuple[int, int],  **kw):
        # ensure the parent's __init__ is called
        super().__init__(*args, style=wx.DEFAULT_FRAME_STYLE & ~wx.MAXIMIZE_BOX ^ wx.RESIZE_BORDER,
                         **kw)
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
        self._elements = SortedKeyList(key=lambda e: e.layers)
        self._plugin_elements = set()
        self.hovered_element = None
        self.dragged_element = None
        self.reaction_map = defaultdict(set)
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

        bind_handler(DidCommitDragEvent, lambda _: self.OnDidCommitNodePositions())

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

        bounds = Rect(BOUNDS_EPS_VEC, self.realsize * cstate.scale - BOUNDS_EPS_VEC)
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

    def OnWindowDestroy(self, evt):
        evt.Skip()

    def OnIdle(self, evt):
        if not self.LazyRefresh():
            # Not processed; request more
            evt.RequestMore()

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
        snodes = [self.node_idx_map[id] for id in rxn.sources]
        tnodes = [self.node_idx_map[id] for id in rxn.targets]
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
        for elt in self._elements:
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
        self.reaction_map = defaultdict(set)
        for rxn in reactions:
            for nodei in chain(rxn.sources, rxn.targets):
                self.reaction_map[nodei].add(rxn.index)

        self._nodes = nodes
        self._reactions = reactions
        self._compartments = compartments
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

        self._elements = SortedKeyList(select_elements, lambda e: e.layers)
        self._select_box.update(self.GetSelectedNodes(),
                                [c for c in self._compartments if self.sel_compartments_idx.contains(c.index)])
        self._UpdateSelectBoxLayer()
        self._select_box.related_elts = select_elements
        self._elements.add(self._select_box)
        self._minimap.elements = self._elements

        self._UpdateSelectedLists()

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
        pos *= cstate.scale
        # check if out of bounds
        pos = pos.map(lambda e: max(e, 0))

        limit = self.realsize * cstate.scale - Vec2(self.GetSize())
        pos = pos.reduce2(min, limit)

        pos = pos.elem_div(Vec2(self.GetScrollPixelsPerUnit()))
        # need to mult by scale here since self.VirtualPosition is artificially increased, per
        # scale * self.realsize
        self.Scroll(*pos)
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
        self.SetVirtualSize(vsize.x, vsize.y)

        # Important: set virtual size first, then scroll
        self.Scroll(new_scroll.x, new_scroll.y)

        self.zoom_slider.SetValue(self._zoom_level)
        self.zoom_slider.SetPageSize(2)

        self._SetStatusText('zoom', '{:.2f}x'.format(cstate.scale))

        self.LazyRefresh()

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
            logical_pos = Vec2(self.CalcUnscrolledPosition(evt.GetPosition()))

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
                for el in reversed(self._elements):
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

                unscaled_pos = logical_pos / cstate.scale
                adj_pos = unscaled_pos - size / 2

                node = Node(
                    'x',
                    self.net_index,
                    pos=adj_pos,
                    size=size,
                    fill_color=get_theme('node_fill'),
                    border_color=get_theme('node_border'),
                    border_width=get_theme('node_border_width'),
                    comp_idx=self.RectInWhichCompartment(Rect(adj_pos, size)),
                    floatingNode=True,
                    lockNode=False,
                )
                node.position = clamp_rect_pos(node.rect, Rect(Vec2(), self.realsize), BOUNDS_EPS)
                node.id = self._GetUniqueName(node.id, [n.id for n in self._nodes])

                self.controller.start_group()
                self.controller.add_node_g(self._net_index, node)
                self.controller.end_group()

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
            self.LazyRefresh()
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
            self.LazyRefresh()
            evt.Skip()

    def OnRightUp(self, evt):
        """Right mouse button up event handler.

        Note that the handling of the right click up event is determined by the canvas rather
        than by the individual elements.
        """
        device_pos = Vec2(evt.GetPosition())
        logical_pos = Vec2(self.CalcUnscrolledPosition(evt.GetPosition()))

        overlay = self._InWhichOverlay(device_pos)
        if overlay is not None:
            return

        node_el: Optional[NodeElement] = None
        reaction_el: Optional[ReactionElement] = None
        comp_el: Optional[CompartmentElt] = None
        for el in reversed(self._elements):
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


        #def add_item(menu: wx.Menu, menu_name, callback):
        #    qmi = wx.MenuItem(menu, -1, menu_name)
        #    #qmi.SetBitmap(wx.Bitmap('exit.png'))
        #    id_ = menu.Append(qmi) # (-1, menu_name).Id
        #    menu.Bind(wx.EVT_MENU, lambda _: callback(), id=id_)

        def add_item(menu: wx.Menu, menu_name, image_name, callback):
            item = menu.Append(-1, menu_name)

            if image_name != '':
               item.SetBitmap(wx.Bitmap(resource_path(image_name)))
            menu.Bind(wx.EVT_MENU, lambda _: callback(), id=item.Id)

        if total_selected != 0:
            add_item(menu, 'Delete', '', self.DeleteSelectedItems)

        if len(selected_nodes) != 0:
            # Only allow align when the none of the nodes are in a compartment. This prevents
            # nodes inside a compartment being arranged outside.
            if not any(node.comp_idx != -1 for node in self.sel_nodes):
                # Only allow alignment if all selected nodes are in the same compartment
                # Add alignment options

                menu.AppendSeparator()
                align_menu = wx.Menu()
                add_item(align_menu, 'Align Left', 'alignLeft_XP.png', lambda: self.AlignSelectedNodes(Alignment.LEFT))
                add_item(align_menu, 'Align Right', 'alignRight_XP.png', lambda: self.AlignSelectedNodes(Alignment.RIGHT))
                add_item(align_menu, 'Align Center', 'alignHorizCenter_XP.png', 
                         lambda: self.AlignSelectedNodes(Alignment.CENTER))
                align_menu.AppendSeparator()
                add_item(align_menu, 'Align Top', 'alignTop_XP.png', lambda: self.AlignSelectedNodes(Alignment.TOP))
                add_item(align_menu, 'Align Bottom', 'AlignBottom_XP.png', 
                         lambda: self.AlignSelectedNodes(Alignment.BOTTOM))
                add_item(align_menu, 'Align Middle', 'alignVertCenter_XP.png', 
                         lambda: self.AlignSelectedNodes(Alignment.MIDDLE))
                align_menu.AppendSeparator()
                add_item(align_menu, 'Grid', 'alignOnGrid_XP.png', lambda: self.AlignSelectedNodes(Alignment.GRID))
                align_menu.AppendSeparator()
                add_item(align_menu, 'Arrange Horizontally', 'alignHorizEqually_XP.png', 
                         lambda: self.AlignSelectedNodes(Alignment.HORIZONTAL))
                add_item(align_menu, 'Arrange Vertically', 'alignVertEqually_XP.png', 
                         lambda: self.AlignSelectedNodes(Alignment.VERTICAL))
                menu.AppendSubMenu(align_menu, text='Align...')

        # Must refresh before the context menu is displayed, otherwise the refresh won't occur
        self.Refresh()
        self.PopupMenu(menu)
        menu.Destroy()

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

    def findMinX(self, l):
        '''
        Find the left-most node's x position
        Args:
            self
            l: the list of indices of the selected nodes
        '''
        xpos = api.get_node_by_index(0, 0).position.x
        for a in l:
            cur = api.get_node_by_index(0, a)
            newX = cur.position.x
            if(newX < xpos):
                xpos = newX
        return xpos

    def findMaxX(self, l):
        '''
        Find the right-most node's x position
        Args:
            self
            l: the list of indices of the selected nodes
        '''
        xpos = api.get_node_by_index(0, 0).position.x
        for a in l:
            cur = api.get_node_by_index(0, a)
            newX = cur.position.x
            if(newX > xpos):
                xpos = newX
        return xpos

    def findMinY(self, l):
        '''
        Find the left-most node's x position
        Args:
            self
            l: the list of indices of the selected nodes
        '''
        ypos = api.get_node_by_index(0, 0).position.y
        for a in l:
            cur = api.get_node_by_index(0, a)
            newY = cur.position.y
            if(newY < ypos):
                ypos = newY
        return ypos

    def findMaxY(self, l):
        '''
        Find the right-most node's x position
        Args:
            self
            l: the list of indices of the selected nodes
        '''
        ypos = api.get_node_by_index(0, 0).position.y
        for a in l:
            cur = api.get_node_by_index(0, a)
            newY = cur.position.y
            if(newY > ypos):
                ypos = newY
        return ypos

    def setDefaultHandles(self):
        with api.group_action():
            for r in api.get_reactions(0):
                handles = api.default_handle_positions(0, r.index)  # centroid, sources, target
                sources = r.sources
                targets = r.targets
                api.set_reaction_center_handle(0, r.index, handles[0])
                count = 1
                for s in sources:
                    api.set_reaction_node_handle(0, r.index, s, True, handles[count])
                    count += 1
                for t in targets:
                    api.set_reaction_node_handle(0, r.index, t, False, handles[count])
                    count += 1

    def AlignSelectedNodes(self, alignment: Alignment):
        """Align the selected nodes. Should be called only when *only* nodes are selected."""
        # The selected nodes are self.sel_nodes
        # To access a file in the resources folder, use
        # Jin_edit:refer to plugins/arrange.py

        if alignment == Alignment.LEFT:
            '''
            Align selected nodes to the left-most node's x position
            '''
            with api.group_action():
                s = api.get_selected_node_indices(0)  # TODO: 2 of these
                xpos = self.findMinX(s)
                for a in s:
                    cur = api.get_node_by_index(0, a)
                    y = cur.position.y
                    newPos = Vec2(xpos, y)
                    api.move_node(0, a, newPos)
                self.setDefaultHandles()

        if alignment == Alignment.RIGHT:
            '''
            Align selected nodes to the right-most node's x position
            '''
            with api.group_action():
                s = api.get_selected_node_indices(0)  # TODO: 2 of these
                xpos = self.findMaxX(s)
                for a in s:
                    cur = api.get_node_by_index(0, a)
                    y = cur.position.y
                    newPos = Vec2(xpos, y)
                    api.move_node(0, a, newPos)
                self.setDefaultHandles()

        if alignment == Alignment.CENTER:
            '''
            Align selected nodes to the relative center of the x positions of the nodes
            '''
            with api.group_action():
                s = api.get_selected_node_indices(0)  # TODO: 2 of these
                xMin = self.findMinX(s)
                xMax = self.findMaxX(s)
                xpos = math.floor((xMax + xMin)/2)
                for a in s:
                    cur = api.get_node_by_index(0, a)
                    y = cur.position.y
                    newPos = Vec2(xpos, y)
                    api.move_node(0, a, newPos)
                self.setDefaultHandles()

        if alignment == Alignment.TOP:
            with api.group_action():
                s = api.get_selected_node_indices(0)  # TODO: 2 of these
                ypos = self.findMinY(s)
                for a in s:
                    cur = api.get_node_by_index(0, a)
                    x = cur.position.x
                    newPos = Vec2(x, ypos)
                    api.move_node(0, a, newPos)
                self.setDefaultHandles()

        if alignment == Alignment.BOTTOM:
            with api.group_action():
                s = api.get_selected_node_indices(0)  # TODO: 2 of these
                ypos = self.findMaxY(s)
                for a in s:
                    cur = api.get_node_by_index(0, a)
                    x = cur.position.x
                    newPos = Vec2(x, ypos)
                    api.move_node(0, a, newPos)
                self.setDefaultHandles()

        if alignment == Alignment.MIDDLE:
            '''
            Align selected nodes to the relative center of the x positions of the nodes
            '''
            with api.group_action():
                s = api.get_selected_node_indices(0)  # TODO: 2 of these
                yMin = self.findMinY(s)
                yMax = self.findMaxY(s)
                ypos = math.floor((yMax + yMin)/2)
                for a in s:
                    cur = api.get_node_by_index(0, a)
                    x = cur.position.x
                    newPos = Vec2(x, ypos)
                    api.move_node(0, a, newPos)
                self.setDefaultHandles()

        if alignment == Alignment.GRID:
            '''
            Align selected nodes in a net grid manner
            '''
            with api.group_action():
                s = api.get_selected_node_indices(0)
                x = 40
                y = 40
                count = 1
                for a in s:
                    api.move_node(0, a, position=Vec2(x, y))
                    x = x + 130
                    if count % 5 == 0:
                        y = y + 130
                        x = 40
                    count = count + 1
                self.setDefaultHandles()

        if alignment == Alignment.HORIZONTAL:
            with api.group_action():
                s = api.get_selected_node_indices(0)  # TODO: 2 of these
                yMin = self.findMinY(s)
                yMax = self.findMaxY(s)
                ypos = math.floor((yMax + yMin)/2)
                x = 40
                for a in s:
                    newPos = Vec2(x, ypos)
                    api.move_node(0, a, newPos)
                    x = x + 130
                self.setDefaultHandles()

        if alignment == Alignment.VERTICAL:
            with api.group_action():
                s = api.get_selected_node_indices(0)  # TODO: 2 of these
                xMin = self.findMinX(s)
                xMax = self.findMaxX(s)
                xpos = math.floor((xMax + xMin)/2)
                y = 40
                for a in s:
                    newPos = Vec2(xpos, y)
                    api.move_node(0, a, newPos)
                    y = y + 130
                self.setDefaultHandles()

        #raise NotImplementedError('Align Not Implemented!')

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

                size = self._drag_rect.size / cstate.scale
                # make sure the compartment is at least of some size
                adj_size = Vec2(max(size.x, get_setting('min_comp_width')),
                                max(size.y, get_setting('min_comp_height')))
                # compute position
                size_diff = adj_size - self._drag_rect.size
                # center position if drag_rect size has been adjusted
                pos = self._drag_rect.position / cstate.scale - size_diff / 2

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
            logical_pos = self.CalcScrolledPositionFloat(device_pos)
            if self.dragged_element is not None:
                self.dragged_element.on_left_up(logical_pos)
                self.dragged_element = None
            elif self.hovered_element is not None:
                self.hovered_element.on_mouse_leave(logical_pos)
                self.hovered_element = None
            elif evt.LeftIsDown():
                for el in reversed(self._elements):
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
        assert isinstance(evt, wx.MouseEvent)
        redraw = False
        try:
            device_pos = Vec2(evt.GetPosition())
            logical_pos = Vec2(self.CalcUnscrolledPosition(evt.GetPosition()))
            self._cursor_logical_pos = logical_pos
            rxn_radius = get_theme('reaction_radius')

            if self._drag_selecting:
                assert evt.leftIsDown
                topleft = Vec2(min(logical_pos.x, self._drag_select_start.x),
                               min(logical_pos.y, self._drag_select_start.y))
                botright = Vec2(max(logical_pos.x, self._drag_select_start.x),
                                max(logical_pos.y, self._drag_select_start.y))
                self._drag_rect = Rect(topleft, botright - topleft)
                if cstate.input_mode == InputMode.SELECT:
                    selected_nodes = [n for n in self._nodes
                                      if rects_overlap(n.s_rect, self._drag_rect)]
                    selected_comps = [c for c in self._compartments
                                      if rects_overlap(c.rect * cstate.scale, self._drag_rect)]
                    selected_rxns = [re.reaction for re in self._reaction_elements
                                     if rects_overlap(circle_bounds(
                                         re.bezier.real_center * cstate.scale, rxn_radius * cstate.scale),
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
            if cstate.input_mode == InputMode.SELECT:
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
                for el in reversed(self._elements):
                    if not el.enabled:
                        continue
                    if el.pos_inside(logical_pos):
                        hovered = el
                        break

                if hovered is not None and hovered is self.hovered_element:
                    moved = self.hovered_element.on_mouse_move(logical_pos)
                    redraw = moved
                else:
                    if self.hovered_element is not None:
                        self.hovered_element.on_mouse_leave(logical_pos)
                    if hovered is not None:
                        hovered.on_mouse_enter(logical_pos)
                    redraw = True
                    self.hovered_element = hovered
        finally:
            if redraw:
                self.LazyRefresh()
            evt.Skip()

    def LazyRefresh(self) -> bool:
        now = time.time() * 1000
        diff = now - self._last_refresh
        if diff < self.MILLIS_PER_REFRESH:
            return False
        else:
            self._last_refresh = int(now)
            self.Refresh()
            return True

    def OnPaint(self, evt):
        self._accum_frames += 1
        now = time.time() * 1000
        diff = now - self._last_fps_update
        if diff >= 1000:
            self._last_fps_update = int(now)
            fps = int(self._accum_frames / diff * 1000)
            self._SetStatusText('fps', 'refreshes/sec: {}'.format(int(fps)))
            self._accum_frames = 0
        # Update cursor status text here
        status_text = repr(self._cursor_logical_pos)
        self._SetStatusText('cursor', status_text)
        self.SetOverlayPositions()  # have to do this here to prevent jitters

        dc = wx.PaintDC(self)

        # transform for drawing to scrolled coordinates
        self.DoPrepareDC(dc)

        # Draw everything
        gc = self.DrawToDC(dc)

        # Draw minimap
        self._minimap.DoPaint(gc)

        post_event(DidPaintCanvasEvent(gc))

    def DrawActiveRectToImage(self):
        """Draw to image only the active rectangle -- bounding rect of nodes, reactions, & compartments
        """
        bounding_rect = self.GetBoundingRect()
        if bounding_rect is None:
            return None
        
        bounding_rect = padded_rect(bounding_rect, padding=10)
        bounding_rect = wx.Rect(*bounding_rect.position, *bounding_rect.size)
        bounding_rect.Intersect(wx.Rect(0, 0, *self.realsize))

        bmp = wx.Bitmap(*self.realsize)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        self.DrawToDC(dc)
        img = bmp.ConvertToImage()
        ret = img.GetSubImage(bounding_rect)
        return ret

    def DrawToDC(self, dc):
        # Create graphics context since we need transparency
        gc = wx.GraphicsContext.Create(dc)

        if gc:
            # Draw gray background
            draw_rect(
                gc,
                Rect(Vec2(), Vec2(self.GetVirtualSize())),
                fill=get_theme('canvas_outside_bg'),
            )
            # Draw background
            draw_rect(
                gc,
                Rect(Vec2(), self.realsize * cstate.scale),
                fill=get_theme('canvas_bg'),
            )

            # Draw nodes
            within_comp = None
            if cstate.input_mode == InputMode.ADD_NODES and self._cursor_logical_pos is not None:
                size = Vec2(get_theme('node_width'), get_theme('node_height'))
                pos = self._cursor_logical_pos - size/2
                within_comp = self.RectInWhichCompartment(Rect(pos, size))
            elif self._select_box.special_mode == SelectBox.SMode.NODES_IN_ONE and self.dragged_element is not None:
                within_comp = self.InWhichCompartment(self._select_box.nodes)

            # create font for nodes
            for el in self._elements:
                if not el.enabled:
                    continue
                if isinstance(el, CompartmentElt) and el.compartment.index == within_comp:
                    # Highlight compartment that will be dropped in.
                    el.on_paint(gc, highlight=True)
                else:
                    el.on_paint(gc)

            # TODO Put this in SelectionChanged
            sel_rects = ([n.rect * cstate.scale for n in self.sel_nodes] +
                         [c.rect * cstate.scale for c in self.sel_comps])

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
                              corner_radius=get_theme('node_corner_radius'))

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
        return gc

    def ResetLayer(self, elt: CanvasElement, layers: Layer):
        if elt in self._elements:
            self._elements.remove(elt)
        elt.set_layers(layers)
        self._elements.add(elt)

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

    def OnDidCommitNodePositions(self):
        """Update reaction Bezier handles after nodes are dragged."""
        for elt in self._reaction_elements:
            elt.commit_node_pos()

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
        for el in reversed(self._elements):
            if isinstance(el, CompartmentElt):
                comp = cast(CompartmentElt, el).compartment
                comp_rect = comp.rect
                if all(comp_rect.contains(n.rect) for n in nodes):
                    return comp.index
        return -1

    def RectInWhichCompartment(self, rect: Rect) -> int:
        """Same as InWhichCompartment but for a single rect"""
        for el in reversed(self._elements):
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
        for node_idx in sel_nodes_idx:
            if len(self.reaction_map[node_idx] & rem_rxn) != 0:
                bound_node = None
                for node in self.nodes:
                    if node.index == node_idx:
                        bound_node = node

                assert bound_node is not None
                self.ShowWarningDialog("Could not delete node '{}', as one or more reactions \
depend on it.".format(bound_node.id))
                self.logger.warning("Tried and failed to delete bound node '{}' with index '{}'"
                                    .format(bound_node.id, node_idx))
                return

        self.controller.start_group()
        sel_comp_idx = self.sel_compartments_idx.item_copy()
        for index in sel_reactions_idx:
            self.controller.delete_reaction(self._net_index, index)
        for index in sel_nodes_idx:
            self.controller.delete_node(self._net_index, index)
        for index in sel_comp_idx:
            self.controller.delete_compartment(self._net_index, index)
        post_event(DidDeleteEvent(node_indices=sel_nodes_idx, reaction_indices=sel_reactions_idx,
                                  compartment_indices=sel_comp_idx))

        self.controller.end_group()

    def SelectAll(self):
        with self._SelectGroupEvent():
            self.sel_nodes_idx.set_item({n.index for n in self._nodes})
            self.sel_reactions_idx.set_item({r.index for r in self._reactions})
            self.sel_compartments_idx.set_item({c.index for c in self._compartments})
        self.LazyRefresh()

    def SelectAllNodes(self):
        with self._SelectGroupEvent():
            self.sel_nodes_idx.set_item({n.index for n in self._nodes})
        self.LazyRefresh()

    def SelectAllReactions(self):
        with self._SelectGroupEvent():
            self.sel_reactions_idx.set_item({r.index for r in self._reactions})
        self.LazyRefresh()

    def ClearCurrentSelection(self):
        """Clear the current highest level of selection.

        If there are reactants or products marked, clear those. OTherwise clear selected nodes and
        reactions.
        """
        if len(self._reactant_idx) + len(self._product_idx) != 0:
            self._reactant_idx = set()
            self._product_idx = set()
            self.LazyRefresh()
        else:
            with self._SelectGroupEvent():
                self.sel_nodes_idx.set_item(set())
                self.sel_reactions_idx.set_item(set())
                self.sel_compartments_idx.set_item(set())
            self.LazyRefresh()

    def MarkSelectedAsReactants(self):
        self._reactant_idx = self.sel_nodes_idx.item_copy()
        self.LazyRefresh()

    def MarkSelectedAsProducts(self):
        self._product_idx = self.sel_nodes_idx.item_copy()
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
            handle_positions=default_handle_positions(centroid, sources, targets)
        )
        self.controller.add_reaction_g(self._net_index, reaction)
        self._reactant_idx.clear()
        self._product_idx.clear()
        with self._SelectGroupEvent():
            self.sel_nodes_idx.set_item(set())
            self.sel_compartments_idx.set_item(set())
            self.sel_reactions_idx.set_item(
                {self.controller.get_reaction_index(self._net_index, id)})
        self.LazyRefresh()

    def CopySelected(self):
        self._copied_nodes = copy.deepcopy(self.GetSelectedNodes())
        # TODO copy reactions and compartments too

    def CutSelected(self):
        self.CopySelected()
        self.DeleteSelectedItems()

    def Paste(self):
        pasted_ids = set()
        all_ids = {n.id for n in self._nodes}

        self.controller.start_group()
        # get unique IDs
        for node in self._copied_nodes:
            node.id = self._GetUniqueName(node.id, pasted_ids, all_ids)
            node.position += Vec2.repeat(20)
            pasted_ids.add(node.id)
            self._nodes.append(node)  # add this for the event handlers to see
            self.controller.add_node_g(self._net_index, node)

        self.controller.end_group()  # calls UpdateMultiSelect in a moment
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
        self._elements.add(element)

    def RemovePluginElement(self, net_index: int, element: CanvasElement):
        if element not in self._plugin_elements:
            raise ValueError("Tried to remove an element that is not on canvas.")
        self._plugin_elements.remove(element)
        self._elements.remove(element)

    def GetReactionCentroids(self, net_index: int) -> Dict[int, Vec2]:
        """Helper method for ReactionForm to get access to the centroid positions.
        """
        return {r.reaction.index: r.bezier.centroid for r in self._reaction_elements}
