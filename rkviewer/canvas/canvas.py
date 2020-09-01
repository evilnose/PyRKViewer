"""The interface of canvas for wxPython."""
# pylint: disable=maybe-no-member
import wx
from itertools import chain
import typing
import copy
from enum import Enum, unique
from typing import Collection, FrozenSet, Optional, Any, Sequence, Set, Tuple, List, Dict
from .elements import CanvasElement, LayeredElements, NodeElement, ReactionElement, SelectBox
from .state import cstate
from .events import DidDragMoveNodesEvent, DidDragResizeNodesEvent, \
    SelectionDidUpdateEvent, DidUpdateCanvasEvent
from .geometry import Vec2, Rect, padded_rect, rects_overlap, within_rect, clamp_rect_pos
from .data import Node, init_bezier, Reaction
from .observer import Observer, SetSubject
from .utils import get_nodes_by_idx, draw_rect
from .overlays import CanvasOverlay, Minimap
from ..mvc import IController
from ..utils import convert_position
from ..config import theme, settings


BOUNDS_EPS = 0
"""The padding around the canvas to ensure nodes are not moved out of bounds due to floating pont
issues.
"""
BOUNDS_EPS_VEC = Vec2.repeat(BOUNDS_EPS)
"""2D bounds vector formed from BOUNDS_EPS"""


@unique
class InputMode(Enum):
    """Enum for the current input mode of the canvas."""
    SELECT = 'Select'
    ADD = 'Add'
    ZOOM = 'Zoom'

    def __str__(self):
        return str(self.value)


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
        selected_idx: The set of indices of the currently selected nodes.
        sel_reactions_idx: The set of indices of the currently selected reactions.
        drag_selected_idx: The set of indices tentatively selected during dragging. This is added
                           to selected_idx only after the user has stopped drag-selecting.
        hovered_element: The element over which the mouse is hovering, or None.
        zoom_slider: The zoom slider widget.
        input_mode: The current input mode.
    """
    MIN_ZOOM_LEVEL: int = -7
    MAX_ZOOM_LEVEL: int = 7
    NODE_LAYER = 1
    REACTION_LAYER = 2
    SELECT_BOX_LAYER = 10

    controller: IController
    realsize: Vec2
    selected_idx: SetSubject
    sel_reactions_idx: SetSubject
    drag_selected_idx: Set[int]
    hovered_element: Optional[CanvasElement]
    zoom_slider: wx.Slider

    #: Current network index. Right now this is always 0 since there is only one tab.
    _net_index: int
    _nodes: List[Node]  #: List of Node instances. This contains data needed to render them.
    _reactions: List[Reaction]  #: List of ReactionBezier instances.
    _elements: LayeredElements
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
    _mouse_outside_frame: bool
    _copied_nodes: List[Node]  #: Copy of nodes currently in clipboard

    def __init__(self, controller: IController, *args, realsize: Tuple[int, int], **kw):
        # ensure the parent's __init__ is called
        super().__init__(*args, style=wx.DEFAULT_FRAME_STYLE & ~wx.MAXIMIZE_BOX ^ wx.RESIZE_BORDER,
                         **kw)

        init_bezier()
        self.controller = controller
        self._net_index = 0
        self._nodes = list()
        self._reactions = list()
        self._node_elements = list()
        self._reaction_elements = list()
        self._elements = LayeredElements()
        self.hovered_element = None
        self.dragged_element = None

        # prevent flickering
        self.SetDoubleBuffered(True)

        # events
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SCROLLWIN, self.OnScroll)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)

        # state variables
        self._input_mode = InputMode.SELECT
        # Set to (0, 0) since this won't be used before it's updated once first
        self._dragged_rel_window = wx.Point()

        self._zoom_level = 0
        self.realsize = Vec2(realsize)
        scroll_width = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
        scroll_height = wx.SystemSettings.GetMetric(wx.SYS_HSCROLL_Y)
        self._scroll_off = Vec2(scroll_width, scroll_height)
        self.SetVirtualSize(*self.realsize)

        bounds = Rect(BOUNDS_EPS_VEC, self.realsize * cstate.scale - BOUNDS_EPS_VEC)
        self._select_box = SelectBox([], bounds, self.controller, self._net_index,
                                     self.CalcScrolledPositionFloat, self.SetCursor,
                                     Canvas.SELECT_BOX_LAYER)
        self.selected_idx = SetSubject()
        self.sel_reactions_idx = SetSubject()
        selection_obs = Observer(lambda _: self._SelectionChanged())
        self.selected_idx.attach(selection_obs)
        self.sel_reactions_idx.attach(selection_obs)
        self._reactant_idx = set()
        self._product_idx = set()

        self.zoom_slider = wx.Slider(self, style=wx.SL_BOTTOM, size=(200, 25))
        self.zoom_slider.SetRange(Canvas.MIN_ZOOM_LEVEL, Canvas.MAX_ZOOM_LEVEL)
        self.zoom_slider.SetBackgroundColour(theme['zoom_slider_bg'])
        self.Bind(wx.EVT_SLIDER, self.OnSlider)

        # Set a placeholder value for position; we will set it later in SetOverlayPositions().
        self._minimap = Minimap(pos=Vec2(), width=200, realsize=self.realsize,
                                window_size=Vec2(self.GetSize()), pos_callback=self.SetOriginPos)
        self._overlays = [self._minimap]

        self._drag_selecting = False
        self._drag_select_start = Vec2()
        self._drag_rect = Rect(Vec2(), Vec2())
        self.drag_selected_idx = set()

        self._status_bar = self.GetTopLevelParent().GetStatusBar()
        assert self._status_bar is not None, "Need to create status bar before creating canvas!"

        status_fields = settings['status_fields']
        assert status_fields is not None
        self._reverse_status = {name: i for i, (name, _) in enumerate(status_fields)}

        self._mouse_outside_frame = True
        self._copied_nodes = list()

        wx.CallAfter(lambda: self.SetZoomLevel(0, Vec2(0, 0)))

        self.SetOverlayPositions()

    @property
    def input_mode(self):
        return self._input_mode

    @input_mode.setter
    def input_mode(self, val: InputMode):
        self._input_mode = val
        if val == InputMode.ADD:
            self.SetCursor(wx.Cursor(wx.CURSOR_CROSS))
        else:
            self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

        self._SetStatusText('mode', str(val))

    @property
    def net_index(self):
        return self._net_index

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

    def _GetReactionCenterRect(self, s_pos: Vec2) -> Rect:
        size = Vec2.repeat(theme['reaction_center_size']) * cstate.scale
        return Rect(s_pos - size / 2, size)

    def _InWhichOverlay(self, pos: Vec2) -> Optional[CanvasOverlay]:
        """If position is within an overlay, return that overlay; otherwise return None.

        Note:
            If the position is within multiple overlays, return the latest added overlay, i.e. the
            overlay with the largest index in the _overlays list.

        Returns:
            An overlay if applicable, or None if not.
        """
        # TODO right now this is hardcoded; in the future add List[CanvasOverlay] attribute
        if within_rect(pos, Rect(self._minimap.position, self._minimap.size)):
            return self._minimap
        return None

    def SetOverlayPositions(self):
        """Set the positions of the overlaid widgets. 

        This should be called in OnPaint so that the overlaid widgets stay in the same relative
        position.
        """
        canvas_size = Vec2(self.GetSize())

        zoom_pos = canvas_size - Vec2(self.zoom_slider.GetSize()) - self._scroll_off
        self.zoom_slider.SetPosition(zoom_pos.to_wx_point())

        # do all the minimap updates here, since this is simpler and less prone to bugs
        minimap_pos = Vec2(self.GetSize()) - self._scroll_off - self._minimap.size
        _, slider_height = self.zoom_slider.GetSize()
        minimap_pos.y -= slider_height + 10
        self._minimap.position = minimap_pos

        self._minimap.window_pos = Vec2(self.CalcUnscrolledPosition(wx.Point(0, 0))) / cstate.scale
        # TODO for windows, need to subtract scroll offset from window size. Need to test if this
        # is true for Mac and Linux, however. -Gary
        self._minimap.window_size = Vec2(self.GetSize()) / cstate.scale - self._scroll_off
        self._minimap.realsize = self.realsize
        self._minimap.nodes = self._nodes

    def CreateNodeElement(self, node: Node) -> NodeElement:
        return NodeElement(node, self, self.CalcScrolledPositionFloat, Canvas.NODE_LAYER)

    def CreateReactionElement(self, rxn: Reaction) -> ReactionElement:
        return ReactionElement(rxn, self, self.CalcScrolledPositionFloat, Canvas.REACTION_LAYER)

    def Reset(self, nodes: List[Node], reactions: List[Reaction]):
        """Update the list of nodes and apply the current scale."""
        self._nodes = nodes
        self._reactions = reactions
        node_elements: List[CanvasElement] = [self.CreateNodeElement(n) for n in nodes]
        reaction_elements: List[CanvasElement] = [self.CreateReactionElement(r) for r in reactions]
        select_elements = node_elements + reaction_elements
        self._elements = LayeredElements(select_elements)
        self._select_box.update_nodes(self._GetSelectedNodes())
        self._select_box.related_elts = select_elements
        self._elements.add(self._select_box)

        idx = frozenset(n.index for n in nodes)
        self.selected_idx.set_item(self.selected_idx.item_copy() & idx)  # cull removed nodes

        evt = DidUpdateCanvasEvent(nodes=self._nodes, reactions=self._reactions)
        wx.PostEvent(self, evt)

    def _SetStatusText(self, name: str, text: str):
        idx = self._reverse_status[name]
        self._status_bar.SetStatusText(text, idx)

    def SetOriginPos(self, pos: Vec2):
        """Set the origin position (position of the topleft corner) to pos by scrolling."""
        pos *= cstate.scale
        # check if out of bounds
        pos.x = max(pos.x, 0)
        pos.y = max(pos.y, 0)

        limit = self.realsize * cstate.scale - Vec2(self.GetSize())
        pos.x = min(pos.x, limit.x)
        pos.y = min(pos.y, limit.x)

        pos = pos.elem_div(Vec2(self.GetScrollPixelsPerUnit()))
        # need to mult by scale here since self.VirtualPosition is artificially increased, per
        # scale * self.realsize
        self.Scroll(pos.x, pos.y)

    def SetZoomLevel(self, zoom: int, anchor: Vec2):
        """Zoom in/out with the given anchor.

        The anchor point stays at the same relative position after
        zooming. Note that the anchor position is scrolled position,
        i.e. device position
        """
        assert zoom >= Canvas.MIN_ZOOM_LEVEL and zoom <= Canvas.MAX_ZOOM_LEVEL
        self._zoom_level = zoom
        old_scale = cstate.scale
        cstate.scale = 1.2 ** zoom

        # adjust scroll position
        logical = Vec2(self.CalcUnscrolledPosition(anchor.to_wx_point()))
        scaled = logical * \
            (cstate.scale / old_scale)
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
        self.SetOverlayPositions()

        self.zoom_slider.SetValue(self._zoom_level)
        self.zoom_slider.SetPageSize(2)

        self._SetStatusText('zoom', '{:.2f}x'.format(cstate.scale))

        self.Refresh()

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

    @convert_position
    def OnLeftDown(self, evt):
        try:
            device_pos = evt.GetPosition()
            # Check if clicked on overlay using device_pos
            overlay = self._InWhichOverlay(device_pos)
            if overlay is not None:
                overlay.hovering = True
                overlay.OnLeftDown(evt)
                return

            for ol in self._overlays:
                if ol is not overlay and ol.hovering:
                    ol.hovering = False

            logical_pos = Vec2(self.CalcUnscrolledPosition(evt.GetPosition()))

            if self.input_mode == InputMode.SELECT:
                for el in self._elements.top_down():
                    if el.pos_inside(logical_pos) and el.do_left_down(logical_pos):
                        self.dragged_element = el
                        self._last_drag_pos = logical_pos
                        break
                else:
                    self.dragged_element = None

                node = None
                rxn = None
                if isinstance(self.dragged_element, NodeElement):
                    n_elem = typing.cast(NodeElement, self.dragged_element)
                    node = n_elem.node
                elif isinstance(self.dragged_element, ReactionElement):
                    r_elem = typing.cast(ReactionElement, self.dragged_element)
                    rxn = r_elem.reaction

                # not resizing or dragging
                if cstate.multi_select:
                    if rxn is not None:
                        if rxn.index in self.sel_reactions_idx.item_copy():
                            self.sel_reactions_idx.remove(rxn.index)
                        else:
                            self.sel_reactions_idx.add(rxn.index)
                    elif node is not None:
                        if node.index in self.selected_idx.item_copy():
                            self.selected_idx.remove(node.index)
                        else:
                            self.selected_idx.add(node.index)
                else:
                    if rxn is not None:
                        self.sel_reactions_idx.set_item({rxn.index})
                        self.selected_idx.set_item(set())
                    elif node is not None:
                        self.selected_idx.set_item({node.index})
                        self.sel_reactions_idx.set_item(set())
                    elif self.dragged_element is None:
                        # clear selected nodes
                        self.selected_idx.set_item(set())
                        self.sel_reactions_idx.set_item(set())

                # if clicked on a new node, immediately allow dragging on the
                # updated select box
                if not cstate.multi_select and node and self._select_box.pos_inside(logical_pos):
                    self._select_box.do_mouse_enter(logical_pos)
                    good = self._select_box.do_left_down(logical_pos)
                    assert good
                    self.dragged_element = self._select_box
                    return

                # clicked on nothing; drag-selecting
                if self.dragged_element is None:
                    self._drag_selecting = True
                    self._drag_select_start = logical_pos
                    self._drag_rect = Rect(self._drag_select_start, Vec2())
                    self.drag_selected_idx = set()

            elif self.input_mode == InputMode.ADD:
                size = Vec2(theme['node_width'], theme['node_height'])

                unscaled_pos = logical_pos / cstate.scale
                adj_pos = unscaled_pos - size / 2

                node = Node(
                    'x',
                    pos=adj_pos,
                    size=size,
                    fill_color=theme['node_fill'],
                    border_color=theme['node_border'],
                    border_width=theme['node_border_width'],
                )
                node.s_position = clamp_rect_pos(node.s_rect, Rect(Vec2(), self.realsize *
                                                                   cstate.scale), BOUNDS_EPS)
                node.id_ = self._GetUniqueName(node.id_, [n.id_ for n in self._nodes])
                self.controller.try_add_node_g(self._net_index, node)
                index = self.controller.get_node_index(self._net_index, node.id_)
                self.selected_idx.set_item({index})
                self.sel_reactions_idx.set_item(set())
                self.Refresh()
            elif self.input_mode == InputMode.ZOOM:
                zooming_in = not wx.GetKeyState(wx.WXK_SHIFT)
                self.IncrementZoom(zooming_in, Vec2(device_pos))

        finally:
            self.Refresh()
            evt.Skip()
            if not evt.foreign:
                wx.CallAfter(self.SetFocus)

    @convert_position
    def OnLeftUp(self, evt):
        try:
            self._EndDrag(evt, False)
        finally:
            self.Refresh()
            evt.Skip()

    # TODO improve this. we might want a special mouseLeftWindow event
    def _EndDrag(self, evt: wx.Event, keep_dragging: bool):
        """Send the updated node positions and sizes to the controller.

        This is called after a dragging/resizing operation has completed, i.e. in OnLeftUp and
        OnLeaveWindow. Set keep_dragging to True if want to keep dragging later, as long as mouse
        is held down.
        """
        device_pos = Vec2(evt.GetPosition())
        overlay = self._InWhichOverlay(device_pos)

        if self._minimap.dragging:
            if not keep_dragging:
                self._minimap.OnLeftUp(evt)
        elif self._drag_selecting:
            self._drag_selecting = False
            self.selected_idx.set_item(self.selected_idx.item_copy() | self.drag_selected_idx)
        elif self.input_mode == InputMode.SELECT:
            # perform left_up on dragged_element if it exists, or just find the node under the
            # cursor
            logical_pos = self.CalcScrolledPositionFloat(device_pos)
            if self.dragged_element is not None:
                self.dragged_element.do_left_up(logical_pos)
                self.dragged_element = None
            else:
                for el in self._elements.top_down():
                    if el.pos_inside(logical_pos) and el.do_left_up(logical_pos):
                        return

        if overlay is not None:
            overlay.OnLeftUp(evt)

    def CalcScrolledPositionFloat(self, pos: Vec2) -> Vec2:
        """Convert logical position to scrolled (device) position, retaining floating point.

        self.CalcScrolledPosition() converts the input floats to ints. This is needed if better
        accuracy is needed.
        """
        return Vec2(self.CalcScrolledPosition(wx.Point(0, 0))) + pos

    @convert_position
    def OnMotion(self, evt):
        assert isinstance(evt, wx.MouseEvent)
        redraw = False
        try:
            device_pos = Vec2(evt.GetPosition())
            logical_pos = Vec2(self.CalcUnscrolledPosition(evt.GetPosition()))
            status_text = repr(logical_pos)
            self._SetStatusText('cursor', status_text)

            # dragging takes priority here
            if self.input_mode == InputMode.SELECT:
                if evt.leftIsDown:  # dragging
                    if self._drag_selecting:
                        topleft = Vec2(min(logical_pos.x, self._drag_select_start.x),
                                       min(logical_pos.y, self._drag_select_start.y))
                        botright = Vec2(max(logical_pos.x, self._drag_select_start.x),
                                        max(logical_pos.y, self._drag_select_start.y))
                        self._drag_rect = Rect(topleft, botright - topleft)
                        selected_nodes = [n for n in self._nodes if rects_overlap(n.s_rect,
                                                                                  self._drag_rect)]
                        self.drag_selected_idx = set(n.index for n in selected_nodes)
                        redraw = True
                        return

                    if self.dragged_element is not None:
                        rel_pos = logical_pos - self._last_drag_pos
                        if self.dragged_element.do_mouse_drag(logical_pos, rel_pos):
                            redraw = True
                        self._last_drag_pos = rel_pos

                        # TODO may want to move this into the element
                        if self.dragged_element == self._select_box:
                            if self._select_box.mode == SelectBox.Mode.MOVING:
                                new_positions = [n.position for n in self._GetSelectedNodes()]
                                evt = DidDragMoveNodesEvent(indices=self.selected_idx,
                                                            new_positions=new_positions)
                                wx.PostEvent(self, evt)
                            else:
                                new_sizes = [n.size for n in self._GetSelectedNodes()]
                                evt = DidDragResizeNodesEvent(indices=self.selected_idx,
                                                              new_sizes=new_sizes)
                                wx.PostEvent(self, evt)

                    elif self._minimap.dragging:
                        self._minimap.OnMotion(evt)
                        redraw = True
                else:
                    overlay = self._InWhichOverlay(device_pos)
                    if overlay is not None:
                        overlay.OnMotion(evt)
                        overlay.hovering = True
                        redraw = True
                    else:
                        hovered: Optional[CanvasElement] = None
                        for el in self._elements.top_down():
                            if el.pos_inside(logical_pos):
                                hovered = el
                                break

                        if self.hovered_element is not hovered:
                            if self.hovered_element is not None:
                                self.hovered_element.do_mouse_leave(logical_pos)
                            if hovered is not None:
                                hovered.do_mouse_enter(logical_pos)
                            redraw = True
                            self.hovered_element = hovered
                        elif hovered is not None:
                            # still in the same hovered element
                            moved = self.hovered_element.do_mouse_move(logical_pos)
                            if moved:
                                redraw = True

                    # un-hover all other overlays TODO keep track of the currently hovering overlay
                    for ol in self._overlays:
                        if ol is not overlay and ol.hovering:
                            ol.hovering = False
                            redraw = True
        finally:
            if redraw:
                self.Refresh()
            evt.Skip()

    def OnPaint(self, evt):
        self.SetOverlayPositions()
        dc = wx.PaintDC(self)
        # Create graphics context from it
        gc = wx.GraphicsContext.Create(dc)

        if gc:
            # Draw background
            origin = Vec2(self.CalcScrolledPosition(wx.Point(0, 0)))
            draw_rect(
                gc,
                Rect(origin, self.realsize * cstate.scale),
                fill=theme['canvas_bg'],
            )

            # Draw nodes
            # create font for nodes
            for el in self._elements.bottom_up():
                el.do_paint(gc)

            # Draw reactant and product marker outlines
            def draw_reaction_outline(color: wx.Colour):
                draw_rect(
                    gc,
                    padded_rect(self._ToScrolledRect(node.s_rect),
                                theme['react_node_padding'] * cstate.scale),
                    fill=None,
                    border=color,
                    border_width=theme['react_node_border_width'],
                    border_style=wx.PENSTYLE_LONG_DASH,
                )

            reactants = get_nodes_by_idx(self._nodes, self._reactant_idx)
            for node in reactants:
                draw_reaction_outline(theme['reactant_border'])

            products = get_nodes_by_idx(self._nodes, self._product_idx)
            for node in products:
                draw_reaction_outline(theme['product_border'])

            # Draw drag-selection rect
            if self._drag_selecting:
                draw_rect(
                    gc,
                    self._ToScrolledRect(self._drag_rect),
                    fill=theme['drag_fill'],
                    border=theme['drag_border'],
                    border_width=theme['drag_border_width'],
                )

            # Draw minimap
            self._minimap.DoPaint(gc)

    def _ToScrolledRect(self, rect: Rect) -> Rect:
        """Helper that converts rectangle to scrolled (device) position."""
        adj_pos = Vec2(self.CalcScrolledPosition(rect.position.to_wx_point()))
        return Rect(adj_pos, rect.size)

    def _DrawRectOutline(self, gc: wx.GraphicsContext, rect: Rect):
        """Draw the outline around a selected node, given its scaled rect.

        Note: the given rect will be modified.
        """

        # change position to device coordinates for drawing
        rect = self._ToScrolledRect(rect)
        rect = padded_rect(rect, theme['select_outline_padding'] * cstate.scale)

        # draw rect
        draw_rect(gc, rect, border=theme['select_box_color'],
                  border_width=theme['select_outline_width'])

    def _GetSelectedNodes(self) -> List[Node]:
        """Get the list of selected nodes using self.selected_idx."""
        return get_nodes_by_idx(self._nodes, self.selected_idx.item_copy())

    def _GetNodeResizeHandleRects(self, outline_rect: Rect) -> List[Rect]:
        """Helper that computes the scaled positions and sizes of the resize handles.

        Args:
            pos (Vec2): The position of the top-left corner of the node outline.
            size (Vec2): The size of the node outline.

        Returns:
            List[Tuple[Vec2, Vec2]]: A list of (pos, size) tuples representing the resize handle
            rectangles. They are ordered such that the top-left handle is the first element, and
            all other handles follow in clockwise fashion.
        """
        pos, size = outline_rect.as_tuple()
        centers = [pos, pos + Vec2(size.x / 2, 0),
                   pos + Vec2(size.x, 0), pos + Vec2(size.x, size.y / 2),
                   pos + size, pos + Vec2(size.x / 2, size.y),
                   pos + Vec2(0, size.y), pos + Vec2(0, size.y / 2)]
        side = theme['select_handle_length']

        return [Rect(c - Vec2.repeat(side/2), Vec2.repeat(side)) for c in centers]

    def OnScroll(self, evt):
        # Need to use wx.CallAfter() to ensure the scroll event is finished before we update the
        # position of the dragged node
        wx.CallAfter(self.Refresh)
        evt.Skip()

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
        screen_pos = evt.EventObject.ClientToScreen(evt.GetPosition())
        root_frame = self.GetTopLevelParent()
        fw, fh = root_frame.GetClientSize()
        frame_pos = root_frame.ScreenToClient(screen_pos)
        # if mouse is leave frame (i.e. the root application window), issue OnLeftUp event.
        if frame_pos.x < 0 or frame_pos.y < 0 or frame_pos.x >= fw or frame_pos.y >= fh:
            self._mouse_outside_frame = True
            self._EndDrag(evt, True)

    def _SelectionChanged(self):
        """Callback passed to observer for when the node/reaction selection has changed."""
        node_idx = self.selected_idx.item_copy()
        rxn_idx = self.sel_reactions_idx.item_copy()
        self._select_box.update_nodes([n for n in self._nodes if n.index in node_idx])
        wx.PostEvent(self, SelectionDidUpdateEvent(node_idx=node_idx, reaction_idx=rxn_idx))

    def DeleteSelectedNodes(self):
        # TODO if node is not free (from iodine), show the error somehow
        # TODO allow deletion of reactions
        if len(self.selected_idx.item_copy()) != 0:
            self.controller.try_start_group()
            for index in self.selected_idx.item_copy():
                self.controller.try_delete_node(self._net_index, index)
            self.controller.try_end_group()

    def SelectAll(self):
        self.selected_idx.set_item({n.index for n in self._nodes})
        self.sel_reactions_idx.set_item({r.index for r in self._reactions})
        self.Refresh()

    def ClearSelection(self):
        self.selected_idx.set_item(set())
        self.sel_reactions_idx.set_item(set())
        self.Refresh()

    def MarkSelectedAsReactants(self):
        self._reactant_idx = self.selected_idx.item_copy()
        # TODO make reactant/product/none state as field of a node?
        self._product_idx -= self._reactant_idx
        self.Refresh()

    def MarkSelectedAsProducts(self):
        self._product_idx = self.selected_idx.item_copy()
        self._reactant_idx -= self._product_idx
        self.Refresh()

    def CreateReactionFromMarked(self, id_='r'):
        if len(self._reactant_idx) == 0 or len(self._product_idx) == 0:
            print('TODO show error if no reactants or products')
            return

        id_ = self._GetUniqueName(id_, [r.id_ for r in self._reactions])
        reaction = Reaction(
            id_,
            sources=get_nodes_by_idx(self._nodes, self._reactant_idx),
            targets=get_nodes_by_idx(self._nodes, self._product_idx),
            fill_color=theme['reaction_fill'],
            rate_law='',
        )
        self.controller.try_add_reaction_g(self._net_index, reaction)
        self._reactant_idx.clear()
        self._product_idx.clear()
        self.selected_idx.set_item(set())
        self.sel_reactions_idx.set_item({self.controller.get_reaction_index(self._net_index, id_)})
        self.Refresh()

    def CopySelected(self):
        self._copied_nodes = copy.deepcopy(self._GetSelectedNodes())

    def CutSelected(self):
        self.CopySelected()
        self.DeleteSelectedNodes()

    def Paste(self):
        pasted_ids = set()
        all_ids = {n.id_ for n in self._nodes}

        self.controller.try_start_group()
        # get unique IDs
        for node in self._copied_nodes:
            node.id_ = self._GetUniqueName(node.id_, pasted_ids, all_ids)
            node.position += Vec2.repeat(20)
            pasted_ids.add(node.id_)
            self.controller.try_add_node_g(self._net_index, node)

        self.selected_idx.set_item({self.controller.get_node_index(self._net_index, id_)
                                    for id_ in pasted_ids})
        self.controller.try_end_group()  # calls UpdateMultiSelect in a moment
