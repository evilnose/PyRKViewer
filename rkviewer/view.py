from enum import Enum
from typing import Callable, List, Optional, Tuple, Dict, Any
import copy
# pylint: disable=maybe-no-member
import wx

from .types import Vec2, Node, IView, IController, DEFAULT_THEME
from .widgets import ButtonGroup, DragDrop


class TopToolbar(wx.Panel):
    dragdrop: DragDrop

    def __init__(self, parent, zoom_callback, drop_callback, **kw):
        super().__init__(parent, **kw)

        # TODO add as attribute
        self._zoom_callback = zoom_callback

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        zoom_in_btn = wx.Button(
            self, label="Zoom In")
        # TODO make this a method
        sizer.Add(zoom_in_btn, wx.SizerFlags().Align(
            wx.ALIGN_CENTER_VERTICAL).Border(wx.LEFT, 10))
        zoom_in_btn.Bind(
            wx.EVT_BUTTON, self.OnZoomIn)

        zoom_out_btn = wx.Button(
            self, label="Zoom Out")
        sizer.Add(zoom_out_btn, wx.SizerFlags().Align(
            wx.ALIGN_CENTER_VERTICAL).Border(wx.LEFT, 10))
        zoom_out_btn.Bind(
            wx.EVT_BUTTON, self.OnZoomOut)

        self.dragdrop = DragDrop(
            self, window=parent, drop_callback=drop_callback,
            size=(30, 30))
        self.dragdrop.SetBackgroundColour(
            wx.WHITE)
        sizer.Add(self.dragdrop, wx.SizerFlags().Align(
            wx.ALIGN_CENTER_VERTICAL).Border(wx.LEFT, 10))
        self.SetSizer(sizer)

    def OnZoomIn(self, _):
        self._zoom_callback(True)

    def OnZoomOut(self, _):
        self._zoom_callback(False)


class Toolbar(wx.Panel):
    def __init__(self, *args, toggle_callback, **kw):
        super().__init__(*args, **kw)
        sizer = wx.BoxSizer(wx.VERTICAL)
        select_btn = wx.ToggleButton(
            self, label='&Select')
        sizer.Add(select_btn, wx.SizerFlags().Align(
            wx.ALIGN_CENTER).Border(wx.TOP, 10))
        add_btn = wx.ToggleButton(
            self, label='&Add')
        sizer.Add(add_btn, wx.SizerFlags().Align(
            wx.ALIGN_CENTER).Border(wx.TOP, 10))
        zoom_btn = wx.ToggleButton(
            self, label='&Zoom')
        sizer.Add(zoom_btn, wx.SizerFlags().Align(
            wx.ALIGN_CENTER).Border(wx.TOP, 10))

        btn_group = ButtonGroup(
            self, toggle_callback)
        btn_group.AddButton(select_btn, 'select')
        btn_group.AddButton(add_btn, 'add')
        btn_group.AddButton(zoom_btn, 'zoom')

        self.SetSizer(sizer)


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
            Node is being dragged.
        _dragged_relative (wx.Point): The relative (unscrolled) position of the dragged
            node. This is used to make sure the draggednode stays at the same relative
            position when the panel is scrolled.
        _left_down_pos (Vec2): The last time the "down" event is
            triggered for the left mouse button. This is used to keep track of
            the relative distance traversed for the drag event. Note that this
            is a logical position, i.e. the position relative to the virtual
            origin of the canvas, which may be offscreen.
        _scale (float): The scale (i.e. zoom level) of the displayed elements. The dimensions
            of the elements are multiplied by this number
    """
    controller: IController
    _nodes: List[Node]
    _input_mode: InputMode
    _dragged_node: Optional[Node]
    _dragged_relative: wx.Point
    _left_down_pos: Vec2
    _scale: float
    realsize: Vec2
    theme = Any  # Set as Any for now, since otherwise there was some issues with PyRight

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
        self.Bind(wx.EVT_LEFT_DOWN,
                  self.OnLeftDown)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SCROLLWIN, self.OnScroll)
        self.Bind(wx.EVT_MOUSEWHEEL,
                  self.OnMouseWheel)

        # state variables
        self._input_mode = InputMode.SELECT
        self._dragged_node = None
        # Set to (0, 0) since this won't be used before it's updated once first
        self._dragged_relative = wx.Point()
        self._left_down_pos = Vec2(0, 0)

        self._scale = 1
        self.realsize = Vec2(realsize)
        self.SetVirtualSize(
            self.realsize.x, self.realsize.y)

    @property
    def scale(self):
        return self._scale

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

    def Zoom(self, zooming_in: bool, anchor: Vec2):
        """Zoom in/out with the given anchor.

        The anchor point stays at the same relative position after
        zooming. Note that the anchor position is scrolled position,
        i.e. device position
        """
        old_scale = self._scale
        if zooming_in:
            self._scale *= 1.5
        else:
            self._scale /= 1.5

        # adjust scroll position
        logical = Vec2(self.CalcUnscrolledPosition(
            anchor.to_wx_point()))
        scaled = logical * \
            (self._scale / old_scale)
        newanchor = Vec2(
            self.CalcScrolledPosition(scaled.to_wx_point()))
        # the amount of shift needed to keep anchor at the same position
        shift = newanchor - anchor
        cur_scroll = Vec2(
            self.CalcUnscrolledPosition(0, 0))
        new_scroll = cur_scroll + shift
        # convert to scroll units
        new_scroll = new_scroll.elem_div(
            Vec2(self.GetScrollPixelsPerUnit()))
        self.Scroll(new_scroll.x, new_scroll.y)

        for node in self._nodes:
            node.scale = self._scale

        vsize = self.realsize * self._scale
        self.SetVirtualSize(vsize.x, vsize.y)

        self.Refresh()

    def ZoomCenter(self, zooming_in: bool):
        self.Zoom(zooming_in, Vec2(
            self.GetSize()) / 2)

    def AddNodeRename(self, node: Node) -> str:
        """Add node helper that renames if results in duplicate IDs.
        Return the final ID added.
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
                self.controller.TryAddNode(node)
                return cur_id
            increment += 1

    def OnLeftDown(self, evt):
        scrolledpos = evt.GetPosition()
        # virtual position on the canvas
        self._left_down_pos = scrolledpos
        # actual, unscaled position on the canvas
        real_pos = Vec2(self.CalcUnscrolledPosition(
            scrolledpos)) / self._scale
        if self._input_mode == InputMode.SELECT:
            self._dragged_node = None
            # check if there is node under clicked position
            # consider newly added nodes to be on top
            for node in reversed(self._nodes):
                if node.Contains(real_pos):
                    self._dragged_node = node
                    break

        elif self._input_mode == InputMode.ADD:
            real_pos = Vec2(self.CalcUnscrolledPosition(
                scrolledpos)) / self._scale
            size = Vec2(
                self.theme['node_width'], self.theme['node_height'])

            adj_pos = real_pos - size // 2

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
            zooming_in = not wx.GetKeyState(
                wx.WXK_SHIFT)
            self.Zoom(
                zooming_in, Vec2(scrolledpos))
        evt.Skip()

    def OnMotion(self, evt):
        assert isinstance(evt, wx.MouseEvent)
        if self._input_mode == InputMode.SELECT:
            if evt.leftIsDown:
                if self._dragged_node is not None:
                    assert self._left_down_pos is not None
                    mouse_pos = Vec2(
                        evt.GetPosition())
                    relative = mouse_pos - self._left_down_pos
                    # updated dragged node position
                    self._dragged_node.s_position += relative
                    self._dragged_relative = self.CalcScrolledPosition(
                        self._dragged_node.s_position.to_wx_point())
                    # update _left_down_pos for later dragging
                    self._left_down_pos = mouse_pos
                    self.Refresh()
            else:
                if self._dragged_node is not None:
                    self.controller.TryMoveNode(
                        self._dragged_node)
                    # not dragging anymore
                    self._dragged_node = None
        evt.Skip()

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        # Create graphics context from it
        gc = wx.GraphicsContext.Create(dc)

        if gc:
            font = wx.Font(
                wx.FontInfo(10 * self._scale))
            gfont = gc.CreateFont(font, wx.BLACK)
            gc.SetFont(gfont)

            for node in self._nodes:
                width, height = node.s_size
                x, y = self.CalcScrolledPosition(
                    node.s_position.to_wx_point())
                border_width = node.border_width * self._scale

                # make a path that contains a circle and some lines
                brush = wx.Brush(
                    node.fill_color, wx.BRUSHSTYLE_SOLID)
                gc.SetBrush(brush)
                pen = gc.CreatePen(wx.GraphicsPenInfo(
                    node.border_color).Width(border_width))
                gc.SetPen(pen)
                path = gc.CreatePath()
                path.AddRectangle(
                    x, y, width, height)

                gc.FillPath(path)
                gc.StrokePath(path)

                # Draw text
                tw, th, _, _ = gc.GetFullTextExtent(
                    node.id_)
                tx = (width - tw) / 2
                ty = (height - th) / 2
                gc.DrawText(
                    node.id_, tx + x, ty + y)

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

    def OnNodeDrop(self, pos):
        print('dropped')


class MainPanel(wx.Panel):
    controller: IController
    theme: Dict[str, Any]
    dragdrop: DragDrop

    def __init__(self, parent, controller: IController, theme: Dict[str, Any]):
        # ensure the parent's __init__ is called
        super().__init__(parent, style=wx.CLIP_CHILDREN)
        self.SetBackgroundColour(wx.Colour(176, 176, 176))
        self.controller = controller
        self.theme = theme
        self.canvas = Canvas(self.controller, self, size=(theme['canvas_width'], theme['canvas_height']),
                             realsize=(4 * theme['canvas_width'],
                                       4 * theme['canvas_height']),
                             theme=theme)
        self.canvas.SetScrollRate(10, 10)
        self.canvas.SetBackgroundColour(
            theme['canvas_bg'])

        # create a panel in the frame
        self.toolbar = Toolbar(self,
                               size=(theme['left_toolbar_width'],
                                     theme['canvas_height']),
                               toggle_callback=self.canvas.SetInputMode)
        self.toolbar.SetBackgroundColour(
            theme['toolbar_bg'])

        self.top_toolbar = TopToolbar(self,
                                      size=(theme['canvas_width'],
                                            theme['top_toolbar_height']),
                                      zoom_callback=self.canvas.ZoomCenter,
                                      drop_callback=self.OnNodeDrop,
                                      )
        self.top_toolbar.SetBackgroundColour(
            theme['toolbar_bg'])
        #self.dragdrop = self.top_toolbar.dragdrop

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.buffer = None

        # and create a sizer to manage the layout of child widgets
        sizer = wx.FlexGridSizer(
            cols=2, rows=2, vgap=5, hgap=5)

        # For the items (non-spacers),
        # The 0th element of the tuple is the element itself
        # The 1st element is 1 for the canvas, so that only it expands during resize
        # The 2nd element is wx.EXPAND for all, so that the element expands to fill
        #   their grid cell.
        sizer.AddMany([
            # Add spacer at (0, 0)
            (theme['left_toolbar_width'],
             theme['top_toolbar_height']),
            # Add top toolbar at (0, 1)
            (self.top_toolbar, 0, wx.EXPAND),
            # Add toolbar at (1, 0)
            (self.toolbar, 0, wx.EXPAND),
            # Add canvas at (1, 1)
            (self.canvas, 1, wx.EXPAND),
        ])

        # The 1st col and row are growable, i.e. the cell the canvas is in
        sizer.AddGrowableCol(1, 1)
        sizer.AddGrowableRow(1, 1)

        # TODO Set the sizer and *prevent the user from resizing it to a smaller size*
        # are we sure we want this?
        self.SetSizer(sizer)

    def OnPaint(self, evt):
        evt.Skip()
        '''
        if self.dragdrop.dragging:
            scale = self.canvas.scale

            x, y = self.dragdrop.position

            width = self.theme['node_width'] * scale
            height = self.theme['node_height'] * scale
            border_width = self.theme['node_border_width'] * scale

            # make a path that contains a circle and some lines
            brush = wx.Brush(
                self.theme['node_fill'], wx.BRUSHSTYLE_SOLID)
            dc.SetBrush(brush)
            pen = wx.Pen(colour=self.theme['node_border'],
                         width=border_width)
            dc.SetPen(pen)
            dc.DrawRectangle(x, y, width, height)
        '''

    def OnNodeDrop(self, obj: wx.Window, pos: wx.Point):
        if obj == self.canvas:
            self.canvas.OnNodeDrop(pos)


class View(IView):
    def __init__(self, theme=DEFAULT_THEME):
        self.controller = None
        self.theme = copy.copy(theme)

    def BindController(self, controller: IController):
        self.controller = controller

    def MainLoop(self):
        assert self.controller is not None
        app = wx.App()
        frm = wx.Frame(None, title='RK Network Viewer', size=(800, 600))
        window = MainPanel(frm, self.controller, theme=self.theme)
        self.canvas_panel = window.canvas
        frm.Show()
        app.MainLoop()

    def UpdateAll(self, nodes: List[Node]):
        """Update the list of nodes.

        Note that View takes ownership of the list of nodes and may modify it.
        """
        self.canvas_panel.ResetNodes(nodes)
        self.canvas_panel.Refresh()
