from typing import List, Dict, Any
import copy
# pylint: disable=maybe-no-member
import wx

from .types import  Node, IView, IController, DEFAULT_THEME
from .canvas import Canvas
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
        self.canvas = Canvas(self.controller, self,
                             size=(theme['canvas_width'], theme['canvas_height']),
                             realsize=(4 * theme['canvas_width'], 4 * theme['canvas_height']),
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
        self.SetSizerAndFit(sizer)

    def OnNodeDrop(self, obj: wx.Window, pos: wx.Point):
        if obj == self.canvas:
            self.canvas.OnNodeDrop(pos)


class MyFrame(wx.Frame):
    def __init__(self, controller: IController, theme, **kw):
        super().__init__(None, **kw)
        self.main_panel = MainPanel(self, controller, theme=theme)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.main_panel, 1, wx.EXPAND)
        self.SetSizerAndFit(sizer)


class View(IView):
    def __init__(self, theme=DEFAULT_THEME):
        self.controller = None
        self.theme = copy.copy(theme)

    def BindController(self, controller: IController):
        self.controller = controller

    def MainLoop(self):
        assert self.controller is not None
        app = wx.App()
        frm = MyFrame(self.controller, self.theme, title='RK Network Viewer')
        self.canvas_panel = frm.main_panel.canvas
        frm.Show()
        app.MainLoop()

    def UpdateAll(self, nodes: List[Node]):
        """Update the list of nodes.

        Note that View takes ownership of the list of nodes and may modify it.
        """
        self.canvas_panel.ResetNodes(nodes)
        self.canvas_panel.Refresh()
