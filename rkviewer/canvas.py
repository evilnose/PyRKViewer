# pylint: disable=maybe-no-member
from rkviewer.canvaswidgets import CanvasOverlay, Minimap
import wx
from enum import Enum
from typing import Optional, Any, Tuple, List, Dict
from .utils import WithinRect, DrawRect
from .types import Rect, Vec2, Node, IController


class InputMode(Enum):
    SELECT = 1
    ADD = 2
    ZOOM = 3


class Canvas(wx.ScrolledWindow):
    """The main panel onto which nodes, reactions, etc. will be drawn

    Attributes:
        controller (IController): The associated controller instance.
        nodes (List[Node]): List of Node instances. This contains data needed
            rendering them.
        _input_mode (InputMode): The current input mode, e.g. SELECT, ADD, etc.
        _dragged_node (Optional[Node]): The node current dragged, or None if no
            Node is being dragged. TODO make this a list and change this to IDs
        _dragged_relative (wx.Point): The relative (unscrolled) position of the dragged
            node. This is used to make sure the draggednode stays at the same relative
            position when the panel is scrolled.
        _left_down_pos (Vec2): The last time the "down" event is
            triggered for the left mouse button. This is used to keep track of
            the relative distance traversed for the drag event. Note that this
            is a logical position, i.e. the position relative to the virtual
            origin of the canvas, which may be offscreen.
        _scale (float): The scale (i.e. zoom level) of the displayed elements. The dimensions
                        of the elements are multiplied by this number. This should be updated whenever
                        _zoom_level is.
        _zoom_level (int): Discrete zoom level directly related to _scale. Negative for zoom out,
                           0 for no zoom, positive for zoom in. Needed by slider.
        realsize (Vec2): The actual, total size of canvas, including the part offscreen.
        theme (Any): In fact a dictionary that holds the theme data. See types.DEFAULT_THEME
                     for fields. Set to 'Any' type for now due to some issues
                     with Dict typing.
        _selected_ids (List[str]): The list of ids of the selected nodes.
        _resize_handle (int): -1 if currently not resizing node, or 0-3 meaning  which vertex is
                              being dragged. 0: top-left corner, and other vertices follow clockwise
    """
    controller: IController
    _nodes: List[Node]
    _input_mode: InputMode
    _dragged_node: Optional[Node]
    _dragged_relative: wx.Point
    _left_down_pos: Vec2
    _zoom_level: int
    _scale: float
    realsize: Vec2
    theme = Any  # Set as Any for now, since otherwise there was some issues with PyRight
    _selected_ids: List[str]
    _resize_handle: int
    _minimap: Minimap

    MIN_ZOOM_LEVEL = -10
    MAX_ZOOM_LEVEL = 10

    def __init__(self, controller: IController, *args, realsize: Tuple[int, int],
                 theme: Dict[str, Any], **kw):
        # ensure the parent's __init__ is called
        super().__init__(*args, **kw)

        self.controller = controller
        self.theme = theme
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

        # state variables
        self._input_mode = InputMode.SELECT
        self._dragged_node = None
        # Set to (0, 0) since this won't be used before it's updated once first
        self._dragged_relative = wx.Point()
        self._left_down_pos = Vec2(0, 0)

        self._zoom_level = 0
        self._scale = 1
        self.realsize = Vec2(realsize)
        self.SetVirtualSize(self.realsize.x, self.realsize.y)

        self._selected_ids = list()
        self._resize_handle = -1

        self.zoom_slider = wx.Slider(self, style=wx.SL_BOTTOM, size=(200, 25))
        self.zoom_slider.SetRange(Canvas.MIN_ZOOM_LEVEL, Canvas.MAX_ZOOM_LEVEL)
        self.zoom_slider.SetBackgroundColour(self.theme['zoom_slider_bg'])
        self.Bind(wx.EVT_SLIDER, self.OnSlider)

        self._minimap = Minimap(width=200, realsize=self.realsize, window_pos=Vec2(0, 0),
                                window_size=Vec2(self.GetSize()), pos_callback=self.SetOriginPos)

        # TODO add List[CanvasOverlay] to store all overlays, so that overlay mouse checking code 
        # can be generalized

        self.SetOverlayPositions()

    @property
    def scale(self):
        return self._scale
    
    def InWhichOverlay(self, pos: Vec2) -> Optional[CanvasOverlay]:
        # TODO right now this is hardcoded; in the future add List[CanvasOverlay] attribute
        if WithinRect(pos, Rect(self._minimap.position, self._minimap.size)):
            return self._minimap
        return None

    def SetOverlayPositions(self):
        """Set the positions of the overlaid widgets. 

        This should be called in OnPaint so that the overlaid widgets stay in the same relative
        position.
        """
        canvas_size = Vec2(self.GetSize())
        scroll_width = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
        scroll_height = wx.SystemSettings.GetMetric(wx.SYS_HSCROLL_Y)
        scroll_off = Vec2(scroll_width, scroll_height)

        zoom_pos = canvas_size - Vec2(self.zoom_slider.GetSize()) - scroll_off
        self.zoom_slider.SetPosition(zoom_pos.to_wx_point())

        # do all the minimap updates here, since this is simpler and less prone to bugs
        minimap_pos = Vec2(self.GetSize()) - scroll_off - self._minimap.size
        _, slider_height = self.zoom_slider.GetSize()
        minimap_pos.y -= slider_height + 10
        self._minimap.position = minimap_pos

        self._minimap.window_pos = Vec2(self.CalcUnscrolledPosition(wx.Point(0, 0))) / self._scale
        # TODO for windows, need to subtract scroll offset from window size. Need to test if this
        # is true for Mac and Linux, however. -Gary
        self._minimap.window_size = (Vec2(self.GetSize()) - scroll_off) / self._scale
        self._minimap.realsize = self.realsize
        self._minimap.nodes = self._nodes

    def ResetNodes(self, nodes: List[Node]):
        self._nodes = nodes
        for node in self._nodes:
            node.scale = self._scale

    def SetInputMode(self, mode_str: str):
        """Set input mode based on the mode string"""
        self._input_mode = {
            'select': InputMode.SELECT,
            'add': InputMode.ADD,
            'zoom': InputMode.ZOOM,
        }[mode_str]

    def SetOriginPos(self, pos: Vec2):
        # check if out of bounds
        pos.x = max(pos.x, 0)
        pos.y = max(pos.y, 0)

        limit = Vec2(self.GetVirtualSize()) - Vec2(self.GetSize())
        pos.x = min(pos.x, limit.x)
        pos.y = min(pos.y, limit.x)

        pos = pos.elem_div(Vec2(self.GetScrollPixelsPerUnit()))
        # need to mult by scale here since self.VirtualPosition is artificially increased, per
        # scale * self.realsize
        self.Scroll(pos.x * self._scale, pos.y * self._scale)

    def SetZoomLevel(self, zoom: int, anchor: Vec2):
        """Zoom in/out with the given anchor.

        The anchor point stays at the same relative position after
        zooming. Note that the anchor position is scrolled position,
        i.e. device position
        """
        assert zoom >= Canvas.MIN_ZOOM_LEVEL and zoom <= Canvas.MAX_ZOOM_LEVEL
        self._zoom_level = zoom
        old_scale = self._scale
        self._scale = 1.2 ** zoom

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
        self.Scroll(new_scroll.x, new_scroll.y)
        self.SetOverlayPositions()

        for node in self._nodes:
            node.scale = self._scale

        vsize = self.realsize * self._scale
        self.SetVirtualSize(vsize.x, vsize.y)

        self.zoom_slider.SetValue(self._zoom_level)
        self.zoom_slider.SetPageSize(2)

        self.Refresh()

    def ZoomCenter(self, zooming_in: bool):
        self.IncrementZoom(zooming_in, Vec2(self.GetSize()) / 2)

    def IncrementZoom(self, zooming_in: bool, anchor: Vec2):
        new_zoom = self._zoom_level + (1 if zooming_in else -1)
        if new_zoom < self.MIN_ZOOM_LEVEL or new_zoom > self.MAX_ZOOM_LEVEL:
            return
        self.SetZoomLevel(new_zoom, anchor)

    def AddNodeRename(self, node: Node) -> Optional[str]:
        """Add node helper that renames if results in duplicate IDs.

        Return the final ID added, or None is unsuccessful
        """
        increment = 0
        ids = self.controller.GetListOfNodeIds()
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
                if self.controller.TryAddNode(node):
                    return cur_id
                else:
                    return None
            increment += 1

    def OnLeftDown(self, evt):
        device_pos = Vec2(evt.GetPosition())

        # Check overlays
        overlay = self.InWhichOverlay(device_pos)
        if overlay is not None:
            overlay.OnLeftDown(evt)
            self.Refresh()
            return

        logical_pos = Vec2(self.CalcUnscrolledPosition(evt.GetPosition()))
        self._left_down_pos = device_pos
        reselect = False  # set to true if we might want to select a new node

        if self._input_mode == InputMode.SELECT:
            if len(self._selected_ids) == 0:
                reselect = True
            else:
                # there are selected nodes; test if user clicked inside outline bounds or if user
                # is resizing node
                selected_nodes = self._GetSelectedNodes()

                # TODO remove this once we can select multiple
                assert len(selected_nodes) == 1

                # get dimensions of outline
                node = selected_nodes[0]
                outline_rect = self._GetNodeOutlineRect(node)
                rects = self._GetNodeResizeHandleRects(outline_rect)

                handle = -1
                for i, rect in enumerate(rects):
                    if WithinRect(logical_pos, rect):
                        handle = i
                        break

                if handle >= 0:
                    # resize time
                    self._resize_handle = handle
                else:
                    if WithinRect(logical_pos, outline_rect):
                        # keep selecting this selected node, but need to update self._dragged_node
                        # in case things were redrawn
                        self._dragged_node = self._GetSelectedNodes()[0]
                    else:
                        reselect = True

            if reselect:
                # check if there is node under clicked position
                # consider newly added nodes to be on top
                self._dragged_node = None
                for node in reversed(self._nodes):
                    if WithinRect(logical_pos, Rect(node.s_position, node.s_size)):
                        self._dragged_node = node
                        break

                if self._dragged_node is None:
                    self._selected_ids = list()
                else:
                    self._selected_ids = [self._dragged_node.id_]

            self.Refresh()

        elif self._input_mode == InputMode.ADD:
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
            self.AddNodeRename(node)
            self.Refresh()
        elif self._input_mode == InputMode.ZOOM:
            zooming_in = not wx.GetKeyState(wx.WXK_SHIFT)
            self.IncrementZoom(zooming_in, device_pos)
        evt.Skip()

    def OnLeftUp(self, evt):
        device_pos = Vec2(evt.GetPosition())
        overlay = self.InWhichOverlay(device_pos)
        if overlay is not None:
            overlay.OnLeftUp(evt)
            self.Refresh()
            return

        if self._input_mode == InputMode.SELECT:
            # move dragged node
            if self._dragged_node is not None:
                assert self._resize_handle == -1  # cannot be dragging & resizing at the same time

                self.controller.TryMoveNode(self._dragged_node.id_, self._dragged_node.position)
                # not dragging anymore
                self._dragged_node = None
            elif self._resize_handle != -1:
                assert self._resize_handle >= 0 and self._resize_handle <= 3
                # TODO ask controller to resize
                node = self._GetSelectedNodes()[0]
                self.controller.TryMoveNode(node.id_, node.position)
                self.controller.TrySetNodeSize(node.id_, node.size)
                self._resize_handle = -1  # not resizing anymore

    def OnMotion(self, evt):
        assert isinstance(evt, wx.MouseEvent)

        device_pos = Vec2(evt.GetPosition())
        overlay = self.InWhichOverlay(device_pos)
        if overlay is not None:
            overlay.OnMotion(evt)
            self.Refresh()
            return

        if self._input_mode == InputMode.SELECT:
            if evt.leftIsDown:  # dragging
                if self._dragged_node is not None:
                    assert self._left_down_pos is not None
                    assert self._resize_handle == -1

                    mouse_pos = Vec2(evt.GetPosition())
                    relative = mouse_pos - self._left_down_pos
                    # updated dragged node position
                    self._dragged_node.s_position += relative
                    self._dragged_relative = self.CalcScrolledPosition(
                        self._dragged_node.s_position.to_wx_point())
                    # update _left_down_pos for later dragging
                    self._left_down_pos = mouse_pos
                    self.Refresh()
                elif self._resize_handle != -1:
                    assert self._resize_handle >= 0 and self._resize_handle <= 3
                    # opposite_pt =
                    node = self._GetSelectedNodes()[0]
                    outline = self._GetNodeOutlineRect(node)
                    # get opposite vertex as fixed point
                    fixed_point = outline.NthVertex((self._resize_handle + 2) % 4)
                    dragged_point = outline.NthVertex(self._resize_handle)
                    target_point = Vec2(self.CalcUnscrolledPosition(evt.GetPosition()))

                    orig_diff = dragged_point - fixed_point
                    target_diff = target_point - fixed_point
                    size_ratio = target_diff.elem_div(orig_diff)
                    # convert outline diff to unscaled rect diff
                    rect_diff = node.s_size.elem_mul(size_ratio) / self._scale
                    if abs(rect_diff.x) >= self.theme['min_node_width'] and \
                            abs(rect_diff.y) >= self.theme['min_node_height']:
                        # check that we are not going negative, i.e. "flipping" the node
                        signs = orig_diff.elem_mul(target_diff)
                        if signs.x >= 0 and signs.y >= 0:  # same signs
                            # pos takes the minimum of the x's and y's of any two opposing vertices
                            new_outline_pos = Vec2(min(fixed_point.x, target_point.x),
                                                   min(fixed_point.y, target_point.y))
                            new_pos = new_outline_pos + Vec2.unity() * \
                                self.theme['node_outline_padding']

                            if new_pos.x >= 0 and new_pos.y >= 0:
                                # can resize
                                new_size = rect_diff.elem_abs()
                                node.s_position = new_pos
                                node.size = new_size  # rect_diff is unscaled
                                self.Refresh()

        evt.Skip()

    def OnPaint(self, evt):
        self.SetOverlayPositions()
        dc = wx.PaintDC(self)
        # Create graphics context from it
        gc = wx.GraphicsContext.Create(dc)

        if gc:
            # draw background
            DrawRect(
                gc,
                Rect(Vec2(0, 0), self.realsize * self._scale),
                fill=self.theme['canvas_bg']
            )

            # create font for nodes
            font = wx.Font(
                wx.FontInfo(10 * self._scale))
            gfont = gc.CreateFont(font, wx.BLACK)
            gc.SetFont(gfont)

            # draw nodes
            for node in self._nodes:
                x, y = self.CalcScrolledPosition(node.s_position.to_wx_point())
                width, height = node.s_size
                border_width = node.border_width * self._scale

                DrawRect(
                    gc,
                    Rect(Vec2(x, y), node.s_size),
                    fill=self.theme['node_fill'],
                    border=self.theme['node_border'],
                    border_width=border_width,
                )

                # draw text
                tw, th, _, _ = gc.GetFullTextExtent(
                    node.id_)
                tx = (width - tw) / 2
                ty = (height - th) / 2
                gc.DrawText(
                    node.id_, tx + x, ty + y)

                # draw selected node outlines
                # TODO handle multiple selected
                selected_nodes = self._GetSelectedNodes()
                if len(selected_nodes) != 0:
                    self._DrawNodeOutline(gc, selected_nodes[0])

            self._minimap.Paint(gc)

    def _GetSelectedNodes(self) -> List[Node]:
        """Get the list of selected nodes using self._selected_ids"""
        selected_nodes = [n for n in self._nodes if n.id_ in self._selected_ids]
        assert len(selected_nodes) == len(self._selected_ids)
        return selected_nodes

    def _DrawNodeOutline(self, gc: wx.GraphicsContext, node: Node):
        """Draw the outline around a node.

        This also draws the resize handles (squares on the four quarters)
        """
        pen = gc.CreatePen(wx.GraphicsPenInfo(
            self.theme['node_outline_color']).Width(self.theme['node_outline_width']))
        gc.SetPen(pen)

        outline_rect = self._GetNodeOutlineRect(node)
        pos, size = outline_rect.GetTuple()
        # convert to device position for drawing
        pos = Vec2(self.CalcScrolledPosition(pos.to_wx_point()))

        path = gc.CreatePath()
        path.AddRectangle(pos.x, pos.y, size.x, size.y)
        gc.StrokePath(path)

        brush = wx.Brush(self.theme['node_outline_color'], wx.BRUSHSTYLE_SOLID)
        gc.SetBrush(brush)
        rects = self._GetNodeResizeHandleRects(outline_rect)
        for rect in rects:
            rpos, rsize = rect.GetTuple()
            # convert to device position for drawing
            rpos = Vec2(self.CalcScrolledPosition(rpos.to_wx_point()))
            path = gc.CreatePath()
            path.AddRectangle(rpos.x, rpos.y, rsize.x, rsize.y)
            gc.FillPath(path)

    def _GetNodeOutlineRect(self, node: Node) -> Rect:
        """Helper that computes the scaled position and size of the node outline.

        If scrolled is True, compute the scrolled position instead, i.e. relative to the
        visible canvas.
        """
        # TODO update this for multiple nodes and update documentation too
        realpos = Vec2(node.s_position.to_wx_point())
        pos = realpos - Vec2.unity() * self.theme['node_outline_padding']
        size = node.s_size + Vec2.unity() * 2 * self.theme['node_outline_padding']
        return Rect(pos, size)

    def _GetNodeResizeHandleRects(self, outline_rect: Rect) -> List[Rect]:
        """Helper that computes the scaled positions and sizes of the resize handles.

        Note that one can pass the unpacked return value of _GetNodeOutlineRect() directly to this.

        Args:
            pos (Vec2): The position of the top-left corner of the node outline.
            size (Vec2): The size of the node outline.

        Returns:
            List[Tuple[Vec2, Vec2]]: A list of (pos, size) tuples representing the resize handle
            rectangles. They are ordered such that the top-left handle is the first element, and
            all other handles follow in clockwise fashion.
        """
        pos, size = outline_rect.GetTuple()
        centers = [pos, pos + Vec2(size.x, 0), pos + size, pos + Vec2(0, size.y)]
        side = self.theme['node_handle_length']
        ret = list()
        for center in centers:
            ret.append(Rect(center - Vec2.unity() * side / 2, Vec2.unity() * side))

        return ret

    def OnScroll(self, evt):
        evt.Skip()
        # Need to use wx.CallAfter() to ensure the scroll event is finished before we update the
        # position of the dragged node
        wx.CallAfter(self.AfterScroll)

    def AfterScroll(self):
        # if a Node is being dragged while the window is being scrolled, we would
        # like to keep its position relative  to the scroll window the same
        if self._input_mode == InputMode.SELECT and self._dragged_node is not None:
            self._dragged_node.s_position = Vec2(
                self.CalcUnscrolledPosition(self._dragged_relative))
            self.Refresh()

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

    def OnNodeDrop(self, pos):
        print('dropped')
