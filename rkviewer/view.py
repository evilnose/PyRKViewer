# pylint: disable=maybe-no-member
import wx
import copy
from typing import List, Dict, Any
from .canvas.wx import Canvas, InputMode
from .config import DEFAULT_SETTINGS, DEFAULT_THEME, DEFAULT_SETTINGS
from .mvc import IController, IView
from .utils import Node
from .widgets import ButtonGroup


class TopToolbar(wx.Panel):
    """Toolbar at the top of the app."""

    def __init__(self, parent, zoom_callback, **kw):
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

        self.SetSizer(sizer)

    def OnZoomIn(self, _):
        self._zoom_callback(True)

    def OnZoomOut(self, _):
        self._zoom_callback(False)


class Toolbar(wx.Panel):
    """Toolbar at the left of the app."""

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

        btn_group = ButtonGroup(toggle_callback)
        btn_group.AddButton(select_btn, InputMode.SELECT)
        btn_group.AddButton(add_btn, InputMode.ADD)
        btn_group.AddButton(zoom_btn, InputMode.ZOOM)

        self.SetSizer(sizer)


class MainPanel(wx.Panel):
    """The main panel, which is the only chlid of the root Frame."""
    controller: IController
    theme: Dict[str, Any]

    def __init__(self, parent, controller: IController, theme: Dict[str, Any],
                 settings: Dict[str, Any]):
        # ensure the parent's __init__ is called
        super().__init__(parent, style=wx.CLIP_CHILDREN)
        self.SetBackgroundColour(theme['overall_bg'])
        self.controller = controller
        self.theme = theme
        self.canvas = Canvas(self.controller, self,
                             size=(theme['canvas_width'], theme['canvas_height']),
                             realsize=(4 * theme['canvas_width'], 4 * theme['canvas_height']),
                             theme=theme,
                             settings=settings,
                             )
        self.canvas.SetScrollRate(10, 10)

        # The bg of the available canvas will be drawn by canvas in OnPaint()
        self.canvas.SetBackgroundColour(theme['canvas_outside_bg'])

        def set_input_mode(ident):
            self.canvas.input_mode = ident

        # create a panel in the frame
        self.toolbar = Toolbar(self,
                               size=(theme['left_toolbar_width'],
                                     theme['canvas_height']),
                               toggle_callback=set_input_mode)
        self.toolbar.SetBackgroundColour(theme['toolbar_bg'])

        self.top_toolbar = TopToolbar(self,
                                      size=(theme['canvas_width'],
                                            theme['top_toolbar_height']),
                                      zoom_callback=self.canvas.ZoomCenter)
        self.top_toolbar.SetBackgroundColour(theme['toolbar_bg'])

        self.buffer = None

        # and create a sizer to manage the layout of child widgets
        sizer = wx.FlexGridSizer(cols=2, rows=2, vgap=2, hgap=2)

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

        # Set the sizer and *prevent the user from resizing it to a smaller size*
        # TODO are we sure we want this behavior?
        self.SetSizerAndFit(sizer)

    def OnNodeDrop(self, obj: wx.Window, pos: wx.Point):
        if obj == self.canvas:
            self.canvas.OnNodeDrop(pos)


class MyFrame(wx.Frame):
    """The main frame."""
    def __init__(self, controller: IController, theme, settings, **kw):
        super().__init__(None, **kw)
        status_fields = settings['status_fields']
        assert status_fields is not None
        self.CreateStatusBar(len(DEFAULT_SETTINGS['status_fields']))
        self.SetStatusWidths([width for _, width in status_fields])
        self.main_panel = MainPanel(self, controller, theme=theme, settings=settings)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.main_panel, 1, wx.EXPAND)
        self.SetSizerAndFit(sizer)


class View(IView):
    """Implementation of the view class."""
    def __init__(self, theme=DEFAULT_THEME, settings=DEFAULT_SETTINGS):
        self.controller = None
        self.theme = copy.copy(theme)
        self.settings = copy.copy(settings)

    def BindController(self, controller: IController):
        self.controller = controller

    def MainLoop(self):
        assert self.controller is not None
        app = wx.App()
        frm = MyFrame(self.controller, self.theme, self.settings, title='RK Network Viewer')
        self.canvas_panel = frm.main_panel.canvas
        self.canvas_panel.RegisterAllChildren(frm)
        frm.Show()
        app.MainLoop()

    def UpdateAll(self, nodes: List[Node]):
        """Update the list of nodes.

        Note that View takes ownership of the list of nodes and may modify it.
        """
        self.canvas_panel.ResetNodes(nodes)
        self.canvas_panel.Refresh()
