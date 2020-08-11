"""The interface of canvas for wxPython."""
# pylint: disable=maybe-no-member
import wx
from enum import Enum, unique
from typing import Optional, Any, Set, Tuple, List, Dict
from .widgets import CanvasOverlay, Minimap, MultiSelect
from .utils import clamp_rect_pos, rects_overlap, within_rect, draw_rect
from ..utils import Vec2, Rect, Node
from ..mvc import IController
from ..utils import convert_position


BOUNDS_EPS = 1
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

    _input_mode: InputMode
    _nodes: List[Node]  #: List of Node instances. This contains data needed to render them.
    _zoom_level: int  #: The current zoom level. See SetZoomLevel() for more detail.
    #: The zoom scale. This always corresponds one-to-one with zoom_level. See property for detail.
    _scale: float
    _selected_ids: Set[str]  #: The list of IDs of the currently selected nodes.
    _multiselect: Optional[MultiSelect]  #: The current MultiSelect instance.
    _minimap: Minimap  #: The minimap overlay.
    _overlays: List[CanvasOverlay]  #: The list of overlays. Used when processing click events.
    _drag_selecting: bool  #: If currently dragging the selection rectangle.
    _drag_select_start: Vec2  #: The (logical) mouse position when the user started drag selecting.
    _drag_rect: Rect  #: The current drag-selection rectangle.
    _drag_selected_ids: Set[str]  #: The currently selected nodes using drag-selection rectangle.
    _reverse_status: Dict[str, int]  #: TODO
    _mouse_outside_frame: bool

    def __init__(self, controller: IController, *args, realsize: Tuple[int, int],
                 theme: Dict[str, Any], settings: Dict[str, Any], **kw):
        # ensure the parent's __init__ is called
        super().__init__(*args, **kw)

        self.controller = controller
        self.theme = theme
        self.settings = settings  # TODO document
        self._nodes = list()

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
        self._scale = 1
        self.realsize = Vec2(realsize)
        scroll_width = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
        scroll_height = wx.SystemSettings.GetMetric(wx.SYS_HSCROLL_Y)
        self._scroll_off = Vec2(scroll_width, scroll_height)
        self.SetVirtualSize(*self.realsize)

        self._selected_ids = set()
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
        self._drag_selected_ids = set()

        self._status_bar = self.GetTopLevelParent().GetStatusBar()
        assert self._status_bar is not None, "Need to create status bar before creating canvas!"

        status_fields = self.settings['status_fields']
        assert status_fields is not None
        self._reverse_status = {name: i for i, (name, _) in enumerate(status_fields)}

        self._mouse_outside_frame = True

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
        in_node: Optional[Node] = None
        for node in reversed(self._nodes):
            if within_rect(logical_pos, node.s_rect):
                in_node = node
                break
        return in_node

    def InWhichOverlay(self, pos: Vec2) -> Optional[CanvasOverlay]:
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

    def ResetNodes(self, nodes: List[Node]):
        """Update the list of nodes and apply the current scale."""
        self._nodes = nodes
        for node in self._nodes:
            node.scale = self._scale

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

        for node in self._nodes:
            node.scale = self._scale

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

    def _UpdateMultiSelect(self):
        """Reconstruct the MultiSelect object from the current nodes.

        This should be called before self._multiselect is used, if its list of selected nodes is
        outdated. The list of nodes become outdated when self._nodes is overwritten, chiefly in
        ResetNodes(), or when the list of selected nodes is changed.
        """
        nodes = self._GetSelectedNodes()
        if len(nodes) != 0:
            bounds = Rect(BOUNDS_EPS_VEC, self.realsize * self._scale - BOUNDS_EPS_VEC)
            self._multiselect = MultiSelect(self._GetSelectedNodes(), self.theme,
                                            bounds)
        else:
            self._multiselect = None

    def AddNodeRename(self, node: Node) -> Optional[str]:
        """Add node helper that renames if results in duplicate IDs.

        Return the final ID added, or None is unsuccessful
        """
        increment = 0
        ids = self.controller.get_list_of_node_ids()
        # keep incrementing as long as there is duplicate ID
        while True:
            suffix: str
            if increment == 0:
                suffix = ''
            else:
                suffix = '_{}'.format(increment)
            cur_id = node.id_ + suffix
            # not duplicate; add now
            if cur_id not in ids:
                node.id_ = cur_id
                if self.controller.try_add_node(node):
                    return cur_id
                else:
                    return None
            increment += 1

    @convert_position
    def OnLeftDown(self, evt):
        try:
            device_pos = evt.GetPosition()
            # Check overlays
            overlay = self.InWhichOverlay(device_pos)
            if overlay is not None:
                overlay.hovering = True
                overlay.OnLeftDown(evt)
                return

            for ol in self._overlays:
                if ol is not overlay and ol.hovering:
                    ol.hovering = False

            logical_pos = Vec2(self.CalcUnscrolledPosition(evt.GetPosition()))

            in_node = self._InWhichNode(logical_pos)

            if self.input_mode == InputMode.SELECT:
                if len(self._selected_ids) != 0:
                    assert self._multiselect is not None
                    # there are selected nodes; test if user clicked inside outline bounds or if user
                    # is resizing node
                    selected_nodes = self._GetSelectedNodes()

                    # get dimensions of outline TODO select multiple
                    node = selected_nodes[0]
                    rects = self._GetNodeResizeHandleRects(self._multiselect._bounding_rect)

                    for i, rect in enumerate(rects):
                        if within_rect(logical_pos, rect):
                            self._UpdateMultiSelect()
                            self._multiselect.BeginResize(i)
                            return

                multi = wx.GetKeyState(wx.WXK_CONTROL)

                # if not multi-selecting and clicked within rect, then we definitely drag move
                # the rect. OR, if we are multi-selecting but didn't click on any node, and we
                # clicked within rect, then we drag move the rect as well.
                # The case where we don't drag the drag even though we clicked inside is if
                # multi-selecting and clicked on a node -- in that case we de-select that node.
                if (not multi or in_node is None) and len(self._selected_ids) != 0 and within_rect(
                        logical_pos, self._multiselect._bounding_rect):
                    # re-create a MultiSelect since self.nodes could've changed when mouse
                    # button was released
                    self._UpdateMultiSelect()
                    self._multiselect.BeginDrag(logical_pos)
                    return

                # not resizing or dragging
                if multi:
                    if in_node is not None:
                        if in_node.id_ in self._selected_ids:
                            self._selected_ids.remove(in_node.id_)
                        else:
                            self._selected_ids.add(in_node.id_)
                else:
                    # clear selected nodes
                    self._selected_ids = set()
                    if in_node is not None:
                        self._selected_ids.add(in_node.id_)

                # update multiselect
                self._UpdateMultiSelect()

                if len(self._selected_ids) != 0 and within_rect(
                        logical_pos, self._multiselect._bounding_rect):
                    # re-create a MultiSelect since self.nodes could've changed when mouse
                    # button was released
                    self._UpdateMultiSelect()
                    self._multiselect.BeginDrag(logical_pos)
                    return

                # clicked on nothing; drag-selecting
                if in_node is None:
                    self._drag_selecting = True
                    self._drag_select_start = logical_pos
                    self._drag_rect = Rect(self._drag_select_start, Vec2())
                    self._drag_selected_ids = set()
                    self._multiselect = None

            elif self.input_mode == InputMode.ADD:
                size = Vec2(
                    self.theme['node_width'], self.theme['node_height'])

                unscaled_pos = logical_pos / self._scale
                adj_pos = unscaled_pos - size / 2

                node = Node(
                    id_='x',
                    pos=adj_pos,
                    size=size,
                    fill_color=self.theme['node_fill'],
                    border_color=self.theme['node_border'],
                    border_width=self.theme['node_border_width'],
                    scale=self._scale,
                )
                node.s_position = clamp_rect_pos(node.s_rect, Rect(Vec2(), self.realsize *
                                                                   self._scale), BOUNDS_EPS)
                self.AddNodeRename(node)
                self.Refresh()
            elif self.input_mode == InputMode.ZOOM:
                zooming_in = not wx.GetKeyState(wx.WXK_SHIFT)
                self.IncrementZoom(zooming_in, device_pos)

        finally:
            self.Refresh()
            evt.Skip()

    @convert_position
    def OnLeftUp(self, evt):
        try:
            device_pos = Vec2(evt.GetPosition())
            overlay = self.InWhichOverlay(device_pos)

            if self._minimap.dragging:
                self._minimap.OnLeftUp(evt)
            elif self._drag_selecting:
                self._drag_selecting = False
                self._selected_ids |= self._drag_selected_ids
                self._UpdateMultiSelect()
            elif self.input_mode == InputMode.SELECT:
                # move dragged node
                if self._multiselect is not None:
                    if self._multiselect.dragging:
                        assert not self._multiselect.resizing

                        self.controller.try_start_group()
                        for node in self._GetSelectedNodes():
                            self.controller.try_move_node(node.id_, node.position)
                        self.controller.try_end_group()
                        self._multiselect.EndDrag()
                        return  # return to not check overlays
                    elif self._multiselect.resizing:
                        self.controller.try_start_group()
                        for node in self._GetSelectedNodes():
                            self.controller.try_move_node(node.id_, node.position)
                            self.controller.try_set_node_size(node.id_, node.size)
                        self.controller.try_end_group()
                        self._multiselect.EndResize()
                        return  # return to not check overlays

            if overlay is not None:
                overlay.OnLeftUp(evt)
        finally:
            self.Refresh()

    @convert_position
    def OnMotion(self, evt):
        assert isinstance(evt, wx.MouseEvent)
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
                        self._drag_selected_ids = set(n.id_ for n in selected_nodes)
                        return

                    if self._multiselect is not None:
                        if self._multiselect.dragging:
                            assert not self._minimap.dragging

                            self._multiselect.DoDrag(logical_pos)
                            return
                        elif self._multiselect.resizing:
                            self._multiselect.DoResize(logical_pos)
                            return

            overlay = self.InWhichOverlay(device_pos)
            if overlay is not None:
                overlay.OnMotion(evt)
                overlay.hovering = True
            elif self._minimap.dragging:
                self._minimap.OnMotion(evt)

            for ol in self._overlays:
                if ol is not overlay and ol.hovering:
                    ol.hovering = False
        finally:
            self.Refresh()
            evt.Skip()

    def OnPaint(self, evt):
        self.SetOverlayPositions()
        dc = wx.PaintDC(self)
        # Create graphics context from it
        gc = wx.GraphicsContext.Create(dc)

        if gc:
            # draw background for debugging
            origin = Vec2(self.CalcScrolledPosition(wx.Point(0, 0)))
            draw_rect(
                gc,
                Rect(origin, self.realsize * self._scale),
                fill=self.theme['canvas_bg'],
            )

            # create font for nodes
            font = wx.Font(wx.FontInfo(10 * self._scale))
            gfont = gc.CreateFont(font, wx.BLACK)
            gc.SetFont(gfont)

            # draw nodes
            for node in self._nodes:
                x, y = self.CalcScrolledPosition(node.s_position.to_wx_point())
                width, height = node.s_size
                border_width = node.border_width * self._scale

                draw_rect(
                    gc,
                    Rect(Vec2(x, y), node.s_size),
                    fill=self.theme['node_fill'],
                    border=self.theme['node_border'],
                    border_width=border_width,
                )

                # draw text
                tw, th, _, _ = gc.GetFullTextExtent(node.id_)
                tx = (width - tw) / 2
                ty = (height - th) / 2
                gc.DrawText(node.id_, tx + x, ty + y)

            nodes = self._GetSelectedNodes()

            if self._multiselect is not None:
                width = self.theme['node_outline_width'] if len(nodes) == 1 else \
                    self.theme['select_outline_width']
                self._DrawResizeRect(gc, self._multiselect._bounding_rect, width)
                if len(nodes) > 1:
                    for node in nodes:
                        self._DrawNodeOutline(gc, node.s_rect, node.border_width)

            # draw newly-selected nodes outlines
            if self._drag_selecting:
                for node in self._IdsToNodes(self._selected_ids | self._drag_selected_ids):
                    self._DrawNodeOutline(gc, node.s_rect, node.border_width)

            # draw drag-selection rect
            if self._drag_selecting:
                adj_pos = Vec2(self.CalcScrolledPosition(self._drag_rect.position.to_wx_point()))
                drect = Rect(adj_pos, self._drag_rect.size)
                draw_rect(
                    gc,
                    drect,
                    fill=self.theme['drag_fill'],
                    border=self.theme['drag_border'],
                    border_width=self.theme['drag_border_width'],
                )

            self._minimap.OnPaint(gc)

    def _DrawNodeOutline(self, gc: wx.GraphicsContext, rect: Rect, border_width: float):
        """Draw the outline around a selected node, given its scaled rect.

        Note: the given rect will be modified.
        """
        # change position to device coordinates for drawing
        adj_pos = Vec2(self.CalcScrolledPosition(rect.position.to_wx_point()))
        rect.position = adj_pos

        # add padding and account for border
        rect.position -= Vec2.repeat(self.theme['node_outline_padding'])
        rect.size += Vec2.repeat(
            self.theme['node_outline_padding'] * 2)

        # draw rect
        draw_rect(gc, rect, border=self.theme['select_box_color'],
                  border_width=self.theme['node_outline_width'])

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
        """Get the list of selected nodes using self._selected_ids."""
        return self._IdsToNodes(self._selected_ids)

    def _IdsToNodes(self, ids: Set[str]) -> List[Node]:
        """Map the given list of node IDs to a list of corresponding nodes."""
        nodes = [n for n in self._nodes if n.id_ in ids]
        assert len(nodes) == len(ids)
        return nodes

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
        # dispatch a horizontal scroll event in this case
        if evt.GetWheelAxis() == wx.MOUSE_WHEEL_VERTICAL and \
                wx.GetKeyState(wx.WXK_SHIFT):
            evt.SetWheelAxis(
                wx.MOUSE_WHEEL_HORIZONTAL)
            # need to invert rotation for more intuitive scrolling
            evt.SetWheelRotation(
                -evt.GetWheelRotation())

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
            self.OnLeftUp(evt)

    def OnNodeDrop(self, pos):
        # TODO
        print('dropped')
