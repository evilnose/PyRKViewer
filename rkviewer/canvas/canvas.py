"""The interface of canvas for wxPython."""
# pylint: disable=maybe-no-member
from rkviewer.canvas.events import DidDragMoveNodesEvent, DidDragResizeNodesEvent, \
    DidUpdateSelectionEvent, DidUpdateCanvasEvent
import wx
import copy
from enum import Enum, unique
from typing import Collection, Optional, Any, Set, Tuple, List, Dict
from .reactions import BezierHandle, ReactionBezier, init_bezier, Reaction
from .utils import padded_rect, rects_overlap, within_rect, draw_rect
from .widgets import CanvasOverlay, Minimap, MultiSelect
from ..utils import Vec2, Rect, Node, get_nodes_by_idx, clamp_rect_pos, rgba_to_wx_colour
from ..mvc import IController
from ..utils import convert_position


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

        controller: The associated controller instance.
        theme: In fact a dictionary that holds the theme data. See types.DEFAULT_THEME
                     for fields. Set to 'Any' type for now due to some issues
                     with Dict typing.
        settings: Inherited configuration settings.
        realsize: The actual, total size of canvas, including the part offscreen.
    """
    MIN_ZOOM_LEVEL: int = -7
    MAX_ZOOM_LEVEL: int = 7

    controller: IController
    theme: Dict[str, Any]
    settings: Dict[str, Any]
    realsize: Vec2

    #: Current network index. Right now this is always 0 since there is only one tab.
    _net_index: int
    _input_mode: InputMode
    _nodes: List[Node]  #: List of Node instances. This contains data needed to render them.
    _reactions: List[Reaction]  #: List of ReactionBezier instances.
    _zoom_level: int  #: The current zoom level. See SetZoomLevel() for more detail.
    #: The zoom scale. This always corresponds one-to-one with zoom_level. See property for detail.
    _scale: float
    _selected_idx: Set[int]  #: The list of indices of the currently selected nodes.
    _sel_reactions_idx: Set[int]
    _reactant_idx: Set[int]  #: The list of indices of the currently designated reactant nodes.
    _product_idx: Set[int]  #: Thelist of indices of the currently designated product nodes
    _multiselect: Optional[MultiSelect]  #: The current MultiSelect instance.
    _minimap: Minimap  #: The minimap overlay.
    _overlays: List[CanvasOverlay]  #: The list of overlays. Used when processing click events.
    _drag_selecting: bool  #: If currently dragging the selection rectangle.
    _drag_select_start: Vec2  #: The (logical) mouse position when the user started drag selecting.
    _drag_rect: Rect  #: The current drag-selection rectangle.
    _drag_selected_idx: Set[int]  #: The currently selected nodes using drag-selection rectangle.
    _reverse_status: Dict[str, int]  #: TODO
    _mouse_outside_frame: bool
    _copied_nodes: List[Node]
    _bezier_info: Optional[Tuple[Reaction, BezierHandle]]  #: TODO

    def __init__(self, controller: IController, *args, realsize: Tuple[int, int],
                 theme: Dict[str, Any], settings: Dict[str, Any], **kw):
        # ensure the parent's __init__ is called
        super().__init__(*args, style=wx.DEFAULT_FRAME_STYLE & ~wx.MAXIMIZE_BOX ^ wx.RESIZE_BORDER, **kw)

        init_bezier()
        self.controller = controller
        self.theme = theme
        self.settings = settings  # TODO document
        self._net_index = 0
        self._nodes = list()
        self._reactions = list()

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
        #self.GetTopLevelParent().Bind(wx.EVT_CHAR_HOOK, self.TempOnKeyDown)

        # state variables
        self._input_mode = InputMode.SELECT
        # Set to (0, 0) since this won't be used before it's updated once first
        self._dragged_rel_window = wx.Point()

        self._zoom_level = 0
        self._scale = 1
        self.realsize = Vec2(realsize)
        scroll_width = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
        scroll_height = wx.SystemSettings.GetMetric(wx.SYS_HSCROLL_Y)
        self._scroll_off = Vec2(scroll_width, scroll_height)
        self.SetVirtualSize(*self.realsize)

        self._selected_idx = set()
        self._sel_reactions_idx = set()
        self._reactant_idx = set()
        self._product_idx = set()
        self._multiselect = None

        self.zoom_slider = wx.Slider(self, style=wx.SL_BOTTOM, size=(200, 25))
        self.zoom_slider.SetRange(Canvas.MIN_ZOOM_LEVEL, Canvas.MAX_ZOOM_LEVEL)
        self.zoom_slider.SetBackgroundColour(self.theme['zoom_slider_bg'])
        self.Bind(wx.EVT_SLIDER, self.OnSlider)

        # TODO document everything below
        # Set a placeholder value for position; we will set it later in SetOverlayPositions().
        self._minimap = Minimap(pos=Vec2(), width=200, realsize=self.realsize,
                                window_size=Vec2(self.GetSize()), pos_callback=self.SetOriginPos)
        self._overlays = [self._minimap]

        self._drag_selecting = False
        self._drag_select_start = Vec2()
        self._drag_rect = Rect(Vec2(), Vec2())
        self._drag_selected_idx = set()

        self._status_bar = self.GetTopLevelParent().GetStatusBar()
        assert self._status_bar is not None, "Need to create status bar before creating canvas!"

        status_fields = self.settings['status_fields']
        assert status_fields is not None
        self._reverse_status = {name: i for i, (name, _) in enumerate(status_fields)}

        self._mouse_outside_frame = True
        self._copied_nodes = list()

        self._bezier_info = None

        wx.CallAfter(lambda: self.SetZoomLevel(0, Vec2(0, 0)))

        # TODO add List[CanvasOverlay] to store all overlays, so that overlay mouse checking code
        # can be generalized
        self.SetOverlayPositions()

    @property
    def input_mode(self):
        return self._input_mode

    @input_mode.setter
    def input_mode(self, val: InputMode):
        self._input_mode = val
        self._SetStatusText('mode', str(val))

    @property
    def scale(self):
        """The current zoom scale.

        The positions and sizes of the nodes are multiplied by this number for display.
        """
        return self._scale

    def UpdateSelectedIndices(self, indices: Set[int]):
        self._selected_idx = indices

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

    def _InWhichNode(self, logical_pos: Vec2) -> Optional[Node]:
        """If position is within a node, return that node; otherwise return None.

        Note:
            If position is within multiple nodes,return the latest added node.
        """
        for node in reversed(self._nodes):
            if within_rect(logical_pos, node.s_rect):
                return node
        return None

    def _InWhichReactionCenter(self, logical_pos: Vec2) -> Optional[Reaction]:
        for rxn in reversed(self._reactions):
            if within_rect(logical_pos, self._GetReactionCenterRect(rxn.s_position)):
                return rxn
        return None

    def _GetReactionCenterRect(self, s_pos: Vec2) -> Rect:
        size = Vec2.repeat(self.theme['reaction_center_size']) * self._scale
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

        self._minimap.window_pos = Vec2(self.CalcUnscrolledPosition(wx.Point(0, 0))) / self._scale
        # TODO for windows, need to subtract scroll offset from window size. Need to test if this
        # is true for Mac and Linux, however. -Gary
        self._minimap.window_size = Vec2(self.GetSize()) / self._scale - self._scroll_off
        self._minimap.realsize = self.realsize
        self._minimap.nodes = self._nodes

    def Reset(self, nodes: List[Node], reactions: List[Reaction]):
        """Update the list of nodes and apply the current scale."""
        self._nodes = nodes
        for node in nodes:
            node.scale = self._scale

        self._reactions = reactions
        for rxn in reactions:
            rxn.scale = self._scale

        idx = set(n.index for n in nodes)
        self._selected_idx &= idx  # cull removed nodes

        # update MultiSelect is not dragging (if we are dragging, Reset() must have been called
        # when the mouse exited the window.)
        if self._multiselect:
            self._UpdateMultiSelect()

        evt = DidUpdateCanvasEvent(nodes=self._nodes, reactions=self._reactions)
        wx.PostEvent(self, evt)

    def _SetStatusText(self, name: str, text: str):
        idx = self._reverse_status[name]
        self._status_bar.SetStatusText(text, idx)

    def SetOriginPos(self, pos: Vec2):
        pos *= self._scale
        # check if out of bounds
        pos.x = max(pos.x, 0)
        pos.y = max(pos.y, 0)

        limit = self.realsize * self._scale - Vec2(self.GetSize())
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
        old_scale = self._scale
        self._scale = 1.5 ** zoom

        # adjust scroll position
        logical = Vec2(self.CalcUnscrolledPosition(anchor.to_wx_point()))
        scaled = logical * \
            (self._scale / old_scale)
        newanchor = Vec2(self.CalcScrolledPosition(scaled.to_wx_point()))
        # the amount of shift needed to keep anchor at the same position
        shift = newanchor - anchor
        cur_scroll = Vec2(self.CalcUnscrolledPosition(0, 0))
        new_scroll = cur_scroll + shift
        # convert to scroll units
        new_scroll = new_scroll.elem_div(Vec2(self.GetScrollPixelsPerUnit()))

        # update scales for nodes and reactions
        for node in self._nodes:
            node.scale = self._scale

        for rxn in self._reactions:
            rxn.scale = self._scale

        vsize = self.realsize * self._scale
        self.SetVirtualSize(vsize.x, vsize.y)

        # Important: set virtual size first, then scroll
        self.Scroll(new_scroll.x, new_scroll.y)
        self.SetOverlayPositions()

        self.zoom_slider.SetValue(self._zoom_level)
        self.zoom_slider.SetPageSize(2)

        self._SetStatusText('zoom', '{:.2f}x'.format(self._scale))

        self._UpdateMultiSelect()
        self.Refresh()

    def ZoomCenter(self, zooming_in: bool):
        self.IncrementZoom(zooming_in, Vec2(self.GetSize()) / 2)

    def IncrementZoom(self, zooming_in: bool, anchor: Vec2):
        new_zoom = self._zoom_level + (1 if zooming_in else -1)
        if new_zoom < self.MIN_ZOOM_LEVEL or new_zoom > self.MAX_ZOOM_LEVEL:
            return
        self.SetZoomLevel(new_zoom, anchor)

    def ResetZoom(self):
        self.SetZoomLevel(0, Vec2(self.GetSize()) / 2)

    def _UpdateMultiSelect(self):
        """Reconstruct the MultiSelect object from the current nodes.

        This should be called before self._multiselect is used, if its list of selected nodes is
        outdated. The list of nodes become outdated when self._nodes is overwritten, chiefly in
        Reset(), or when the list of selected nodes is changed.
        """
        nodes = self._GetSelectedNodes()
        if len(nodes) != 0:
            bounds = Rect(BOUNDS_EPS_VEC, self.realsize * self._scale - BOUNDS_EPS_VEC)
            self._multiselect = MultiSelect(self._GetSelectedNodes(), self.theme,
                                            bounds)
        else:
            self._multiselect = None

    def _GetUniqueName(self, base: str, names: Collection[str], *args: Collection[str]) -> str:
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
            ### Check if clicked on overlay using device_pos
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
                if len(self._selected_idx) != 0:
                    assert self._multiselect is not None
                    # there are selected nodes; test if user clicked inside outline bounds or if
                    # user is resizing node
                    selected_nodes = self._GetSelectedNodes()

                    # get dimensions of outline
                    node = selected_nodes[0]
                    rects = self._GetNodeResizeHandleRects(self._multiselect.bounding_rect)

                    ### Check if clicked on resize handle
                    for i, rect in enumerate(rects):
                        if within_rect(logical_pos, rect):
                            self._UpdateMultiSelect()
                            self._multiselect.BeginResize(i)
                            return

                multi = wx.GetKeyState(wx.WXK_CONTROL) or wx.GetKeyState(wx.WXK_SHIFT)

                ### Check if clicked on handle circle
                for rxn in (r for r in self._reactions if r.index in self._sel_reactions_idx):
                    handle = rxn.bezier.on_which_handle(logical_pos)
                    if handle is not None:
                        self._bezier_info = (rxn, handle)
                        return

                self._bezier_info = None

                ### Check if clicked on reaction bezier curve
                in_rxn = None
                for rxn in self._reactions:
                    if rxn.bezier.is_on_curve(logical_pos):
                        in_rxn = rxn
                        break

                ### Check if clicked on node
                in_node = None
                if in_rxn is None:
                    in_node = self._InWhichNode(logical_pos)

                # if not multi-selecting and clicked within rect, then we definitely drag move
                # the rect. OR, if we are multi-selecting but didn't click on any node or reaction,
                # and we clicked within rect, then we drag move the rect as well.
                # The case where we don't drag the rect even though we clicked inside is if
                # multi-selecting and clicked on a node -- in that case we de-select that node.
                if len(self._selected_idx) != 0 and \
                        within_rect(logical_pos, self._multiselect.bounding_rect) and \
                        (not multi or (in_node is None and in_rxn is None)):
                    # re-create a MultiSelect since self._nodes could've changed when mouse
                    # button was released
                    self._UpdateMultiSelect()
                    self._multiselect.BeginDrag(logical_pos)
                    return

                # not resizing or dragging
                if multi:
                    if in_rxn is not None:
                        assert in_rxn.index != -1
                        if in_rxn.index in self._sel_reactions_idx:
                            self._sel_reactions_idx.remove(in_rxn.index)
                        else:
                            self._sel_reactions_idx.add(in_rxn.index)
                    elif in_node is not None:
                        assert in_node.index != -1
                        if in_node.index in self._selected_idx:
                            self._selected_idx.remove(in_node.index)
                        else:
                            self._selected_idx.add(in_node.index)
                else:
                    # clear selected nodes
                    self._selected_idx = set()
                    self._sel_reactions_idx = set()
                    if in_rxn is not None:
                        self._sel_reactions_idx.add(in_rxn.index)
                    elif in_node is not None:
                        self._selected_idx.add(in_node.index)

                # update multiselect
                self._UpdateMultiSelect()
                self._PostUpdateSelection()

                # if clicked within a node, start dragging. Need to check for this again, since
                # a new node may have been selected and the user wants to drag it immediately
                if len(self._selected_idx) != 0 and within_rect(
                        logical_pos, self._multiselect.bounding_rect):
                    # re-create a MultiSelect since self._nodes could've changed when mouse
                    # button was released
                    self._multiselect.BeginDrag(logical_pos)
                    return

                # clicked on nothing; drag-selecting
                if in_node is None:
                    self._drag_selecting = True
                    self._drag_select_start = logical_pos
                    self._drag_rect = Rect(self._drag_select_start, Vec2())
                    self._drag_selected_idx = set()
                    if not multi:
                        self._multiselect = None

            elif self.input_mode == InputMode.ADD:
                size = Vec2(
                    self.theme['node_width'], self.theme['node_height'])

                unscaled_pos = logical_pos / self._scale
                adj_pos = unscaled_pos - size / 2

                node = Node(
                    'x',
                    pos=adj_pos,
                    size=size,
                    fill_color=self.theme['node_fill'],
                    border_color=self.theme['node_border'],
                    border_width=self.theme['node_border_width'],
                    scale=self._scale,
                )
                node.s_position = clamp_rect_pos(node.s_rect, Rect(Vec2(), self.realsize *
                                                                   self._scale), BOUNDS_EPS)
                node.id_ = self._GetUniqueName(node.id_, [n.id_ for n in self._nodes])
                self.controller.try_add_node_g(self._net_index, node)
                self.Refresh()
            elif self.input_mode == InputMode.ZOOM:
                zooming_in = not wx.GetKeyState(wx.WXK_SHIFT)
                self.IncrementZoom(zooming_in, Vec2(device_pos))

        finally:
            self.Refresh()
            evt.Skip()

    @convert_position
    def OnLeftUp(self, evt):
        try:
            self._UpdateNodePosAndSize(evt, False)
        finally:
            self.Refresh()

    def _UpdateNodePosAndSize(self, evt: wx.Event, keep_dragging: bool):
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
            self._drag_selecting = False  # stop multiselect regardless of keep_dragging
            self._selected_idx |= self._drag_selected_idx
            self._UpdateMultiSelect()
            self._PostUpdateSelection()
        elif self.input_mode == InputMode.SELECT:
            # move dragged node
            if self._multiselect is not None:
                if self._multiselect.dragging:
                    assert not self._multiselect.resizing

                    self.controller.try_start_group()
                    for node in self._GetSelectedNodes():
                        self.controller.try_move_node(self._net_index, node.index, node.position)
                    self.controller.try_end_group()
                    if not keep_dragging:
                        self._multiselect.EndDrag()
                    return  # return to not check overlays
                elif self._multiselect.resizing:
                    self.controller.try_start_group()
                    for node in self._GetSelectedNodes():
                        self.controller.try_move_node(self._net_index, node.index, node.position)
                        self.controller.try_set_node_size(self._net_index, node.index, node.size)
                    self.controller.try_end_group()
                    if not keep_dragging:
                        self._multiselect.EndResize()
                    return  # return to not check overlays

        if overlay is not None:
            overlay.OnLeftUp(evt)

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
            if evt.leftIsDown:  # dragging
                if self.input_mode == InputMode.SELECT:
                    if self._drag_selecting:
                        topleft = Vec2(min(logical_pos.x, self._drag_select_start.x),
                                       min(logical_pos.y, self._drag_select_start.y))
                        botright = Vec2(max(logical_pos.x, self._drag_select_start.x),
                                        max(logical_pos.y, self._drag_select_start.y))
                        self._drag_rect = Rect(topleft, botright - topleft)
                        selected_nodes = [n for n in self._nodes if rects_overlap(n.s_rect,
                                                                                  self._drag_rect)]
                        self._drag_selected_idx = set(n.index for n in selected_nodes)
                        redraw = True
                        return

                    if self._bezier_info is not None:
                        rxn, handle = self._bezier_info
                        rxn.bezier.do_move_handle(handle, logical_pos)
                        redraw = True
                        return
                    elif self._multiselect is not None:
                        adjusted = False
                        if self._multiselect.dragging:
                            assert not self._minimap.dragging

                            self._multiselect.DoDrag(logical_pos)

                            # post event
                            new_positions = [n.position for n in self._GetSelectedNodes()]
                            evt = DidDragMoveNodesEvent(indices=self._selected_idx,
                                                        new_positions=new_positions)
                            wx.PostEvent(self, evt)
                            adjusted = True
                        elif self._multiselect.resizing:
                            self._multiselect.DoResize(logical_pos)

                            # post event
                            new_sizes = [n.size for n in self._GetSelectedNodes()]
                            evt = DidDragResizeNodesEvent(indices=self._selected_idx,
                                                          new_sizes=new_sizes)
                            wx.PostEvent(self, evt)
                            adjusted = True

                        if adjusted:
                            for rxn in self._reactions:
                                rxn.update()
                            redraw = True
                            return

            overlay = self._InWhichOverlay(device_pos)
            if overlay is not None:
                overlay.OnMotion(evt)
                overlay.hovering = True
                redraw = True
            elif self._minimap.dragging:
                self._minimap.OnMotion(evt)
                redraw = True

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
            ### Draw background
            origin = Vec2(self.CalcScrolledPosition(wx.Point(0, 0)))
            draw_rect(
                gc,
                Rect(origin, self.realsize * self._scale),
                fill=self.theme['canvas_bg'],
            )

            ### Draw nodes
            # create font for nodes
            font = wx.Font(wx.FontInfo(10 * self._scale))
            gfont = gc.CreateFont(font, wx.BLACK)
            gc.SetFont(gfont)

            for node in self._nodes:
                x, y = self.CalcScrolledPosition(node.s_position.to_wx_point())
                width, height = node.s_size
                border_width = node.border_width * self._scale

                draw_rect(
                    gc,
                    Rect(Vec2(x, y), node.s_size),
                    fill=node.fill_color,
                    border=node.border_color,
                    border_width=border_width,
                )

                # draw text
                tw, th, _, _ = gc.GetFullTextExtent(node.id_)
                tx = (width - tw) / 2
                ty = (height - th) / 2
                gc.DrawText(node.id_, tx + x, ty + y)

            ### Draw outline for selected nodes and bounding box
            cur_selected_idx = self._selected_idx | self._drag_selected_idx
            nodes = get_nodes_by_idx(self._nodes, cur_selected_idx)
            if len(nodes) > 0:
                if len(self._selected_idx) > 0:
                    assert self._multiselect is not None
                    width = self.theme['select_outline_width'] if len(nodes) == 1 else \
                        self.theme['select_outline_width']
                    self._DrawResizeRect(gc, self._multiselect.bounding_rect, width)
                if len(nodes) > 1:
                    for node in nodes:
                        self._DrawRectOutline(gc, node.s_rect)
            
            ### Draw reactions
            # for rxn in self._reactions:
                #size = Vec2.repeat(self.theme['reaction_center_size'])
                #scrolled_pos = self.CalcScrolledPosition(rxn.s_position.to_wx_point())
                #draw_rect(gc, Rect(Vec2(scrolled_pos) - size / 2, size), fill=rxn.fill_color)

            ### Draw reaction Beziers
            for rxn in self._reactions:
                rxn.do_paint(gc, self.CalcScrolledPosition)

            for rxn in (r for r in self._reactions if r.index in self._sel_reactions_idx):
                rxn.do_paint_selected(gc, self.CalcScrolledPosition)

            ### Draw reactant and product marker outlines
            def draw_reaction_outline(color: wx.Colour):
                draw_rect(
                    gc,
                    padded_rect(self._ToScrolledRect(node.s_rect),
                                self.theme['react_node_padding'] * self._scale),
                    fill=None,
                    border=color,
                    border_width=self.theme['react_node_border_width'],
                    border_style=wx.PENSTYLE_LONG_DASH,
                )

            reactants = get_nodes_by_idx(self._nodes, self._reactant_idx)
            for node in reactants:
                draw_reaction_outline(self.theme['reactant_border'])

            products = get_nodes_by_idx(self._nodes, self._product_idx)
            for node in products:
                draw_reaction_outline(self.theme['product_border'])

            ### Draw drag-selection rect
            if self._drag_selecting:
                draw_rect(
                    gc,
                    self._ToScrolledRect(self._drag_rect),
                    fill=self.theme['drag_fill'],
                    border=self.theme['drag_border'],
                    border_width=self.theme['drag_border_width'],
                )

            ### Draw minimap
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
        rect = padded_rect(rect, self.theme['select_outline_padding'] * self._scale)

        # draw rect
        draw_rect(gc, rect, border=self.theme['select_box_color'],
                  border_width=self.theme['select_outline_width'])

    def _DrawResizeRect(self, gc: wx.GraphicsContext, rect: Rect, border_width: float):
        """Draw the outline around a node.

        This also draws the eight resize handles.
        """
        # convert to device position for drawing
        pos, size = rect.as_tuple()
        adj_pos = Vec2(self.CalcScrolledPosition(pos.to_wx_point()))

        # draw main outline
        draw_rect(gc, Rect(adj_pos, size), border=self.theme['select_box_color'],
                  border_width=border_width)

        for handle_rect in self._GetNodeResizeHandleRects(rect):
            # convert to device position for drawing
            rpos, rsize = handle_rect.as_tuple()
            rpos = Vec2(self.CalcScrolledPosition(rpos.to_wx_point()))
            draw_rect(gc, Rect(rpos, rsize), fill=self.theme['select_box_color'])

    def _GetSelectedNodes(self) -> List[Node]:
        """Get the list of selected nodes using self._selected_idx."""
        return get_nodes_by_idx(self._nodes, self._selected_idx)

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
        side = self.theme['select_handle_length']

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
            self._UpdateNodePosAndSize(evt, True)

    def _PostUpdateSelection(self):
        wx.PostEvent(self, DidUpdateSelectionEvent(node_idx=self._selected_idx,
                                                   reaction_idx=self._sel_reactions_idx))

    def DeleteSelectedNodes(self):
        if len(self._selected_idx) != 0:
            assert self._multiselect is not None
            self.controller.try_start_group()
            for index in self._selected_idx:
                self.controller.try_delete_node(self._net_index, index)
            self.controller.try_end_group()

            # controller must have told view to cull the selected IDs
            assert len(self._selected_idx) == 0
            self._UpdateMultiSelect()
            self._PostUpdateSelection()

    def SelectAll(self):
        self._selected_idx = {n.index for n in self._nodes}
        self._sel_reactions_idx = {r.index for r in self._reactions}
        self._UpdateMultiSelect()
        self._PostUpdateSelection()
        self.Refresh()

    def ClearSelection(self):
        self._selected_idx = set()
        self._sel_reactions_idx = set()
        self._UpdateMultiSelect()
        self._PostUpdateSelection()
        self.Refresh()

    def SetReactantsFromSelected(self):
        self._reactant_idx = copy.copy(self._selected_idx)
        # TODO make reactant/product/none state as field of a node?
        self._product_idx -= self._reactant_idx
        self.Refresh()

    def SetProductsFromSelected(self):
        self._product_idx = copy.copy(self._selected_idx)
        self._reactant_idx -= self._product_idx
        self.Refresh()

    def CreateReactionFromSelected(self, id_='r'):
        if len(self._reactant_idx) == 0 or len(self._product_idx) == 0:
            print('TODO show error if no reactants or products')
            return

        id_ = self._GetUniqueName(id_, [r.id_ for r in self._reactions])
        reaction = Reaction(
            id_,
            sources=get_nodes_by_idx(self._nodes, self._reactant_idx),
            targets=get_nodes_by_idx(self._nodes, self._product_idx),
            fill_color=self.theme['reaction_fill'],
        )
        self.controller.try_add_reaction_g(self._net_index, reaction)
        self._reactant_idx = set()
        self._product_idx = set()
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

        self._selected_idx = {self.controller.get_node_index(self._net_index, id_) for
                              id_ in pasted_ids}
        self.controller.try_end_group()

    def OnNodeDrop(self, pos):
        # TODO
        print('dropped')
