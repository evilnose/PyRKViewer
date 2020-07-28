from enum import Enum
from typing import Callable, List, Optional, Tuple
# pylint: disable=maybe-no-member
import wx

from .types import Vec2, Node, IView, IController


class ButtonGroup:
    Callback = Callable[[str], None]  # called with ID as argument
    def __init__(self, parent: wx.Panel, callback: Callback):
        self.parent = parent
        self.callback = callback
        self.buttons = []
        self.selected = None  # should be tuple (button, group_id)

    def AddButton(self, button: wx.ToggleButton, group_id: str):
        # right now there is no type info for wxPython, so this is necessary
        assert isinstance(button, wx.ToggleButton)

        self.buttons.append(button)
        button.Bind(wx.EVT_TOGGLEBUTTON, self._MakeToggleFn(button, group_id))

        # First added button; make it selected
        if self.selected is None:
            self.selected = (button, group_id)
            button.SetValue(True)
            self.callback(group_id)

    def _MakeToggleFn(self, button: wx.ToggleButton, group_id: str):
        # right now there is no type info for wxPython, so this is necessary
        assert isinstance(button, wx.ToggleButton)

        def ret(evt):
            assert self.selected is not None, "There must be at least one button in ButtonGroup!"

            if evt.IsChecked():
                button.SetValue(True)
                selected_btn, selected_id = self.selected
                if selected_id != group_id:
                    selected_btn.SetValue(False)
                    self.selected = (button, group_id)
                    self.callback(group_id)
            else:
                # don't allow de-select
                button.SetValue(True)
        return ret


class Toolbar(wx.Panel):
    def __init__(self, *args, toggle_callback=lambda _: None, **kw):
        super().__init__(*args, **kw)
        self.select_btn = wx.ToggleButton(self, label='&Select')
        self.add_btn = wx.ToggleButton(self, label='&Add')
        btn_group = ButtonGroup(self, toggle_callback)
        btn_group.AddButton(self.select_btn, 'select')
        btn_group.AddButton(self.add_btn, 'add')

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.select_btn, wx.SizerFlags().Align(wx.ALIGN_CENTER).Border(wx.TOP, 10))
        sizer.Add(self.add_btn, wx.SizerFlags().Align(wx.ALIGN_CENTER).Border(wx.TOP, 10))
        self.SetSizer(sizer)


class InputMode(Enum):
    SELECT = 1
    ADD = 2


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
    """
    controller: IController
    nodes: List[Node]
    _input_mode: InputMode
    _dragged_node: Optional[Node]
    _dragged_relative: wx.Point
    _left_down_pos: Vec2

    def __init__(self, controller: IController, *args, **kw):
        # ensure the parent's __init__ is called
        super().__init__(*args, **kw)

        self.controller = controller
        self.nodes = list()

        # prevent flickering
        self.SetDoubleBuffered(True)

        # events
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
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

    def SetInputMode(self, mode_str: str):
        """Set input mode based on the mode string"""
        if mode_str == 'select':
            self._input_mode = InputMode.SELECT
        elif mode_str == 'add':
            self._input_mode = InputMode.ADD
        else:
            assert False, "Unknown input mode '{}'".format(mode_str)

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
                suffix = ' ({})'.format(increment)
            cur_id = node.id_ + suffix
            # not duplicate; add now
            if cur_id not in ids:
                node.id_ = cur_id
                self.controller.TryAddNode(node)
                return cur_id
            increment += 1

    def OnLeftDown(self, evt):
        evt.Skip()
        scrolledpos = evt.GetPosition()
        pos = Vec2(self.CalcUnscrolledPosition(scrolledpos))
        self._left_down_pos = scrolledpos
        if self._input_mode == InputMode.SELECT:
            self._dragged_node = None
            # check if there is node under clicked position
            # consider newly added nodes to be on top
            for node in reversed(self.nodes):
                if node.Contains(pos):
                    self._dragged_node = node
                    break

        elif self._input_mode == InputMode.ADD:
            # TODO move these outside
            DEFAULT_FILL = wx.Colour(0, 255, 0, 50)
            DEFAULT_BORDER = wx.Colour(255, 0, 0, 100)
            DEFAULT_BORDER_WIDTH = 1

            size = Vec2(50, 30)
            adj_pos = pos - size // 2

            node = Node(
                id_='x',
                pos=Vec2(adj_pos.x, adj_pos.y),
                size=size,
                fill_color=DEFAULT_FILL,
                border_color=DEFAULT_BORDER,
                border_width=DEFAULT_BORDER_WIDTH,
            )
            self.AddNodeRename(node)
            self.Refresh()
        else:
            assert False, "Unknown input mode '{}'".format(self._input_mode)

    def OnMotion(self, evt):
        evt.Skip()
        assert isinstance(evt, wx.MouseEvent)
        if self._input_mode == InputMode.SELECT:
            if evt.leftIsDown:
                if self._dragged_node is not None:
                    assert self._left_down_pos is not None
                    mouse_pos = Vec2(evt.GetPosition())
                    relative = mouse_pos - self._left_down_pos
                    # updated dragged node position
                    self._dragged_node.position += relative
                    self._dragged_relative = self.CalcScrolledPosition(
                        self._dragged_node.position.to_wx_point())
                    # update _left_down_pos for later dragging
                    self._left_down_pos = mouse_pos
                    self.Refresh()
            else:
                if self._dragged_node is not None:
                    self.controller.TryMoveNode(self._dragged_node)
                    # not dragging anymore
                    self._dragged_node = None
            
        elif self._input_mode == InputMode.ADD:
            pass
        else:
            assert False, "Unknown input mode '{}'".format(self._input_mode)

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        # Create graphics context from it
        gc = wx.GraphicsContext.Create(dc)

        if gc:
            # TODO don't use global
            for node in self.nodes:
                width, height = node.size
                x, y = self.CalcScrolledPosition(node.position.x, node.position.y)

                # make a path that contains a circle and some lines
                brush = wx.Brush(node.fill_color, wx.BRUSHSTYLE_SOLID)
                gc.SetBrush(brush)
                gc.SetPen(wx.RED_PEN)
                path = gc.CreatePath()
                path.AddRectangle(x, y, width - 1, height - 1)

                gc.FillPath(path)
                gc.StrokePath(path)

    def OnScroll(self, evt):
        evt.Skip()
        # Need to use wx.CallAfter() to ensure the scroll event is finished before we update the
        # position of the dragged node
        wx.CallAfter(self.AfterScroll)

    def AfterScroll(self):
        # if a Node is being dragged while the window is being scrolled, we would
        # like to keep its position relative  to the scroll window the same
        if self._input_mode == InputMode.SELECT and self._dragged_node is not None:
            self._dragged_node.position = Vec2(self.CalcUnscrolledPosition(self._dragged_relative))
            self.Refresh()

    def OnMouseWheel(self, evt):
        # dispatch a horizontal scroll event in this case
        if evt.GetWheelAxis() == wx.MOUSE_WHEEL_VERTICAL and \
            wx.GetKeyState(wx.WXK_SHIFT):
                evt.SetWheelAxis(wx.MOUSE_WHEEL_HORIZONTAL)
                # need to invert rotation for more intuitive scrolling
                evt.SetWheelRotation(-evt.GetWheelRotation())

        evt.Skip()

class MainFrame(wx.Frame):
    controller: IController

    def __init__(self, controller: IController, *args, **kw):
        # ensure the parent's __init__ is called
        super().__init__(*args, **kw)

        self.controller = controller
        # TODO style AND with the style in **kw
        self.canvas = Canvas(self.controller, self, size=(630, 500))
        self.canvas.SetVirtualSize(2000, 1600)
        self.canvas.SetScrollRate(10, 10)
        self.canvas.SetBackgroundColour(wx.WHITE)

        # create a panel in the frame
        self.toolbar = Toolbar(self, size=(120, 500), toggle_callback=self.canvas.SetInputMode)
        self.toolbar.SetBackgroundColour(wx.WHITE)

        # and create a sizer to manage the layout of child widgets
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(
            self.toolbar,
            0,  # No horizontal stretch
            wx.EXPAND |  # Vertical stretch is fine
            wx.ALL,
            10
        )
        sizer.Add(self.canvas,
            1,
            wx.EXPAND |
            wx.ALL,
            10
        )
        # Set the sizer and *prevent the user from resizing it to a smaller size*
        # TODO are we sure we want this?
        self.SetSizerAndFit(sizer)


class View(IView):
    def __init__(self):
        self.controller = None

    def BindController(self, controller: IController):
        self.controller = controller

    def MainLoop(self):
        assert self.controller is not None
        app = wx.App()
        frm = MainFrame(self.controller, None, title='RK Network Viewer', size=(800, 600))
        self.canvas_panel = frm.canvas
        frm.Show()
        app.MainLoop()

    def UpdateAll(self, nodes: List[Node]):
        self.canvas_panel.nodes = nodes
        self.canvas_panel.Refresh()
