"""The main RKView class and associated widgets.
"""
import os
from pathlib import Path
from rkviewer.plugin.classes import CATEGORY_NAMES, PluginCategory
from typing import Any, Callable, Dict, List, Optional, Tuple
import json

# pylint: disable=maybe-no-member
# pylint: disable=no-name-in-module
import wx
from wx.lib.buttons import GenBitmapButton, GenBitmapTextButton
import wx.lib.agw.flatnotebook as fnb
from commentjson.commentjson import JSONLibraryException
from rkviewer.plugin.api import init_api
import wx.adv

import rkviewer
from rkviewer.canvas.geometry import get_bounding_rect
from rkviewer.plugin_manage import PluginManager

from .canvas.canvas import Alignment, Canvas
from .canvas.data import Compartment, Node, Reaction
from .canvas.state import InputMode, cstate
from .config import (DEFAULT_SETTING_FMT, INIT_SETTING_TEXT, get_default_raw_settings, get_setting, get_theme,
                     GetConfigDir, GetThemeSettingsPath, load_theme_settings, pop_settings_err, runtime_vars)
from .events import (CanvasDidUpdateEvent, DidMoveCompartmentsEvent,
                     DidMoveNodesEvent, DidResizeCompartmentsEvent,
                     DidResizeNodesEvent, SelectionDidUpdateEvent,
                     bind_handler)
from .forms import CompartmentForm, NodeForm, ReactionForm
from .mvc import IController, IView
from .utils import ButtonGroup, on_msw, resource_path, start_file
from rkviewer.config import AppSettings


class EditPanel(fnb.FlatNotebook):
    """Panel that displays and allows editing of the details of a node.

    Attributes
        node_form: The actual form widget. This is at the same level as null_message. TODO
        null_message: The widget displayed in place of the form,  when nothing is selected.
    """
    node_form: NodeForm
    reaction_form: ReactionForm
    comp_form: CompartmentForm
    null_message: wx.Panel

    def __init__(self, parent, canvas: Canvas, controller: IController, **kw):
        FNB_STYLE = fnb.FNB_NO_X_BUTTON | fnb.FNB_NO_NAV_BUTTONS | fnb.FNB_NODRAG |  fnb.FNB_DROPDOWN_TABS_LIST | fnb.FNB_RIBBON_TABS
        super().__init__(parent, agwStyle=FNB_STYLE, **kw)
        self.SetTabAreaColour(get_theme('toolbar_bg'))
        self.SetNonActiveTabTextColour(get_theme('toolbar_fg'))
        self.SetActiveTabTextColour(get_theme('active_tab_fg'))
        # self.SetActiveTabColour(get_theme('active_tab_bg'))

        self.canvas = canvas

        self.node_form = NodeForm(self, canvas, controller)
        self.reaction_form = ReactionForm(self, canvas, controller)
        self.comp_form = CompartmentForm(self, canvas, controller)

        self.null_message = wx.Panel(self)
        self.null_message.SetForegroundColour(get_theme('toolbar_fg'))
        self.SetBackgroundColour(get_theme('toolbar_bg'))
        self.null_message.SetBackgroundColour(get_theme('toolbar_bg'))
        text = wx.StaticText(
            self.null_message, label="Nothing is selected.", style=wx.ALIGN_CENTER)
        null_sizer = wx.BoxSizer(wx.HORIZONTAL)
        null_sizer.Add(text, proportion=1, flag=wx.ALIGN_CENTER_VERTICAL)
        self.null_message.SetSizer(null_sizer)
        self.SetCustomPage(self.null_message)

        self.node_form.Hide()
        self.reaction_form.Hide()
        self.comp_form.Hide()
        # overall sizer for alternating form and "nothing selected" displays
        #sizer = wx.BoxSizer(wx.HORIZONTAL)
        #sizer.Add(null_message, proportion=1, flag=wx.ALIGN_CENTER_VERTICAL)
        # self.SetSizer(sizer)

        bind_handler(CanvasDidUpdateEvent, self.OnCanvasDidUpdate)
        bind_handler(SelectionDidUpdateEvent, self.OnSelectionDidUpdate)
        bind_handler(DidMoveNodesEvent, self.OnNodesDidMove)
        bind_handler(DidResizeNodesEvent, self.OnDidResizeNodes)
        bind_handler(DidMoveCompartmentsEvent, self.OnCompartmentsDidMove)
        bind_handler(DidResizeCompartmentsEvent, self.OnDidResizeCompartments)

    def OnCanvasDidUpdate(self, evt):
        self.node_form.UpdateNodes(self.canvas.nodes)
        self.reaction_form.CanvasUpdated(self.canvas.reactions, self.canvas.nodes)
        self.comp_form.UpdateCompartments(self.canvas.compartments)

    def OnSelectionDidUpdate(self, evt):
        focused = self.GetTopLevelParent().FindFocus()
        should_show_nodes = len(evt.node_indices) != 0
        should_show_reactions = len(evt.reaction_indices) != 0
        should_show_comps = len(evt.compartment_indices) != 0
        need_update_nodes = self.node_form.selected_idx != evt.node_indices
        need_update_comps = self.comp_form.selected_idx != evt.compartment_indices

        cur_page = self.GetCurrentPage()

        node_index = -1
        for i in range(self.GetPageCount()):
            if self.GetPage(i) == self.node_form:
                node_index = i
                break

        if need_update_nodes or need_update_comps:
            self.node_form.UpdateSelection(evt.node_indices, comps_selected=should_show_comps)
        if should_show_nodes:
            if node_index == -1:
                self.InsertPage(0, self.node_form, 'Nodes')
        elif node_index != -1:
            # find and remove existing page
            self.RemovePage(node_index)
            self.node_form.Hide()

        reaction_index = -1
        for i in range(self.GetPageCount()):
            if self.GetPage(i) == self.reaction_form:
                reaction_index = i
                break

        if self.reaction_form.selected_idx != evt.reaction_indices:
            self.reaction_form.UpdateSelection(evt.reaction_indices)
        if should_show_reactions:
            if reaction_index == -1:
                self.AddPage(self.reaction_form, 'Reactions')
        elif reaction_index != -1:
            self.RemovePage(reaction_index)
            self.reaction_form.Hide()

        comp_index = -1
        for i in range(self.GetPageCount()):
            if self.GetPage(i) == self.comp_form:
                comp_index = i
                break
        if need_update_comps or need_update_nodes:
            self.comp_form.UpdateSelection(evt.compartment_indices,
                                           nodes_selected=should_show_nodes)
        if should_show_comps:
            if comp_index == -1:
                self.AddPage(self.comp_form, 'Compartments')
        elif comp_index != -1:
            self.RemovePage(comp_index)
            self.comp_form.Hide()

        # set the active tab to the same as before
        if cur_page is not None and self.GetCurrentPage() is not None:
            if cur_page is self.GetCurrentPage():
                self.AdvanceSelection()

        # need to reset focus to canvas, since for some reason FlatNotebook sets focus to the first
        # field in a notebook page after it is added.
        self.GetSizer().Layout()

        if focused:
            # restore focus, since otherwise for some reason the newly added page gets the focus
            focused.SetFocus()

        # need to manually show this for some reason
        if not should_show_nodes and not should_show_reactions and not should_show_comps:
            self.null_message.Show()

    def OnNodesDidMove(self, evt):
        self.node_form.NodesMovedOrResized(evt)

    def OnDidResizeNodes(self, evt):
        self.node_form.NodesMovedOrResized(evt)

    def OnCompartmentsDidMove(self, evt):
        self.comp_form.CompsMovedOrResized(evt)

    def OnDidResizeCompartments(self, evt):
        self.comp_form.CompsMovedOrResized(evt)


class ToolbarItem(wx.Panel):
    def __init__(self, parent, label: str, bitmap: wx.Bitmap, size):
        super().__init__(parent, size=size)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        button = wx.BitmapButton(self, bitmap=bitmap, size=(20, 20))
        # button = GenBitmapButton(self, wx.ID_ANY, bitmap=bitmap,
        #           style=wx.NO_BORDER | wx.BU_EXACTFIT, size=(20, 20))
        # button.SetWindowStyleFlag(wx.SIMPLE_BORDER)
        label_text = wx.StaticText(self, label=label, style=wx.ST_ELLIPSIZE_END |
                                   wx.ALIGN_CENTER_HORIZONTAL, size=(size[0], 20))
        label_text.SetForegroundColour (get_theme ('btn_fg'))
        fontinfo = wx.FontInfo(8)
        label_text.SetFont(wx.Font(fontinfo))
        label_text.SetForegroundColour(get_theme('toolbar_fg'))

        sizerflags = wx.SizerFlags().Align(wx.ALIGN_CENTER_HORIZONTAL)
        self.sizer.Add(button, sizerflags.Border(wx.TOP, 5))
        self.sizer.Add(label_text, sizerflags)
        self.SetSizer(self.sizer)


class Toolbar(wx.Panel):
    SIZER_FLAGS = wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL).Border(wx.LEFT, 10)

    def __init__(self, parent):
        super().__init__(parent)
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)

    def AppendTool(self, label: str, callback: Callable[[], Any], bitmap=None):
        if bitmap is None:
            bitmap = wx.ArtProvider.GetBitmap(wx.ART_MISSING_IMAGE, wx.ART_MENU)

        item = ToolbarItem(self, label, bitmap, (60, self.GetParent().GetSize()[1] - 10))

        self.sizer.Add(item, Toolbar.SIZER_FLAGS)
        item.Bind(wx.EVT_BUTTON, lambda _: callback())
        self.sizer.Layout()

    def AppendCenterSpacer(self):
        """Append a center spacer. Tools added after this will be aligned to the right side.

        """
        self.sizer.Add((0, 0), proportion=1, flag=wx.EXPAND)
        self.sizer.Layout()


class TabbedToolbar(fnb.FlatNotebook):
    """Toolbar with multiple tabs, at the top of the app."""
    manager: PluginManager

    def __init__(self, parent, controller: IController, canvas: Canvas, edit_panel_callback,
                 manager: PluginManager, **kw):
        super().__init__(parent, agwStyle=fnb.FNB_NO_X_BUTTON | fnb.FNB_NODRAG | fnb.FNB_NO_TAB_FOCUS | fnb.FNB_RIBBON_TABS, **kw)
        self.manager = manager
        file_tb = Toolbar(self)
        file_tb.SetForegroundColour (wx.RED)
        file_tb.SetBackgroundColour(get_theme ('toolbar_bg'))
        file_tb.AppendTool('Undo', controller.undo,
                           wx.ArtProvider.GetBitmap(wx.ART_UNDO, wx.ART_MENU))
        file_tb.AppendTool('Redo', controller.redo,
                           wx.ArtProvider.GetBitmap(wx.ART_REDO, wx.ART_MENU))
        file_tb.AppendTool('Zoom In', lambda: canvas.ZoomCenter(True),
                           wx.ArtProvider.GetBitmap(wx.ART_PLUS, wx.ART_MENU))
        file_tb.AppendTool('Zoom Out', lambda: canvas.ZoomCenter(False),
                           wx.ArtProvider.GetBitmap(wx.ART_MINUS, wx.ART_MENU))
        file_tb.AppendCenterSpacer()
        file_tb.AppendTool('Details', edit_panel_callback,
                           wx.ArtProvider.GetBitmap(wx.ART_HELP_SIDE_PANEL, wx.ART_MENU))
        self.AddPage(file_tb, text='Main')

    def AddPluginPages(self):
        categories = self.manager.get_plugins_by_category()
        for cat in PluginCategory:
            if len(categories[cat]) == 0:
                continue

            tb = Toolbar(self)
            for name, callback, bitmap in categories[cat]:
                if bitmap is None:
                    #bitmap = wx.ArtProvider.GetBitmap(wx.ART_MISSING_IMAGE, wx.ART_MENU)
                    bitmap = wx.ArtProvider.GetBitmap(wx.ART_REPORT_VIEW, wx.ART_MENU)
                tb.AppendTool(name, callback, bitmap)
            tb.SetForegroundColour (wx.RED)
            tb.SetBackgroundColour (get_theme ('toolbar_bg'))
            self.AddPage(tb, text=CATEGORY_NAMES[cat])

    def UpdatePluginPages(self):
        page_count = self.GetPageCount()
        for page in range(1,page_count):
            self.DeletePage(1)
        self.AddPluginPages()


class ModePanel(wx.Panel):
    """ModePanel at the left of the app."""

    def __init__(self, *args, toggle_callback, canvas: Canvas, **kw):
        super().__init__(*args, **kw)

        self.btn_group = ButtonGroup(toggle_callback)

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.AppendModeButton('Select', InputMode.SELECT, sizer)
        self.AppendModeButton('+Nodes', InputMode.ADD_NODES, sizer)
        self.AppendModeButton('+Compts', InputMode.ADD_COMPARTMENTS, sizer)
        #self.AppendModeButton('Zoom', InputMode.ZOOM, sizer)

        self.AppendSeparator(sizer)
        self.AppendNormalButton('Reactants', canvas.MarkSelectedAsReactants,
                                sizer, tooltip='Mark selected nodes as reactants')
        self.AppendNormalButton('Products', canvas.MarkSelectedAsProducts,
                                sizer, tooltip='Mark selected nodes as products')
        self.AppendNormalButton('Create Rxn', canvas.CreateReactionFromMarked,
                                sizer, tooltip='Create reaction from marked reactants and products')

        self.SetSizer(sizer)

    def AppendModeButton(self, label: str, mode: InputMode, sizer: wx.Sizer):
        if get_theme ('btn_border'):
            btn = wx.ToggleButton(self, label=label)
        else:
            btn = wx.ToggleButton(self, label=label, style=wx.BORDER_NONE)

        def enter_func(evt):
            btn.SetBackgroundColour(get_theme('btn_hover_bg'))
            btn.SetForegroundColour(get_theme('btn_hover_fg'))

        def exit_func(evt):
            btn.SetBackgroundColour(get_theme('btn_bg'))
            btn.SetForegroundColour(get_theme('btn_fg'))

        btn.Bind(wx.EVT_ENTER_WINDOW, enter_func)
        btn.Bind(wx.EVT_LEAVE_WINDOW, exit_func)

        btn.SetBackgroundColour(get_theme('btn_bg'))
        #font = wx.Font(11, wx.FONTFAMILY_MODERN, 0, 90, underline = False,  faceName ="") # <- if we want to change font style
        btn.SetForegroundColour(get_theme('btn_fg'))
        #btn.SetFont (font)

        sizer.Add(btn, wx.SizerFlags().Align(wx.ALIGN_CENTER).Border(wx.TOP, 10))
        self.btn_group.AddButton(btn, mode)

    def AppendNormalButton(self, label: str, callback, sizer: wx.Sizer, tooltip: str = None):
        if get_theme ('btn_border'):
           btn = wx.Button(self, label=label)
        else:
           btn = wx.Button(self, label=label, style=wx.BORDER_NONE)

        btn.SetBackgroundColour(get_theme ('btn_bg'))
        btn.SetForegroundColour(get_theme ('btn_fg'))
        if tooltip is not None:
            btn.SetToolTip(tooltip)
        btn.Bind(wx.EVT_BUTTON, lambda _: callback())
        sizer.Add(btn, wx.SizerFlags().Align(wx.ALIGN_CENTER).Border(wx.TOP, 10))

    def AppendSeparator(self, sizer: wx.Sizer):
        sizer.Add((0, 10))


class BottomBar(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.SetForegroundColour(get_theme('toolbar_fg'))
        self.SetBackgroundColour(get_theme('toolbar_bg'))
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)

    def CreateSlider(self):
        self.sizer.Add((0, 0), proportion=1, flag=wx.EXPAND)
        zoom_slider = wx.Slider(self, style=wx.SL_BOTTOM | wx.SL_AUTOTICKS, size=(225, 25))
        self.sizer.Add(zoom_slider, wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL))
        self.sizer.Layout()
        return zoom_slider


class MainPanel(wx.Panel):
    """The main panel, which is the only child of the root Frame."""
    # controller: IController
    # canvas: Canvas
    # mode_panel: ModePanel
    # toolbar: TabbedToolbar
    # edit_panel: EditPanel
    # last_save_path: Optional[str]

    def __init__(self, parent, controller: IController, manager: PluginManager):
        # ensure the parent's __init__ is called
        super().__init__(parent, style=wx.CLIP_CHILDREN)
        self.SetBackgroundColour(get_theme('overall_bg'))
        self.controller = controller

        self.bottom_bar = BottomBar(self)
        zoom_slider = self.bottom_bar.CreateSlider()

        self.canvas = Canvas(self.controller, zoom_slider, self,
                             size=(get_theme('canvas_width'),
                                   get_theme('canvas_height')),
                             realsize=(get_theme('real_canvas_width'),
                                       get_theme('real_canvas_height')),)
        self.canvas.SetScrollRate(10, 10)

        # The bg of the available canvas will be drawn by canvas in OnPaint()
        self.canvas.SetBackgroundColour(get_theme('canvas_outside_bg'))

        def set_input_mode(ident): cstate.input_mode = ident

        # create a panel in the frame
        self.mode_panel = ModePanel(self,
                                    size=(get_theme('mode_panel_width'),
                                          get_theme('canvas_height')),
                                    toggle_callback=set_input_mode,
                                    canvas=self.canvas,
                                    )

        self.mode_panel.SetForegroundColour(get_theme('toolbar_fg'))
        self.mode_panel.SetBackgroundColour(get_theme('toolbar_bg'))

        # Note: setting the width to 0 doesn't matter since GridBagSizer is in control of the
        # width.
        self.toolbar = TabbedToolbar(self, controller, self.canvas,
                                     self.ToggleEditPanel, manager,
                                     size=(0, get_theme('toolbar_height')))

        # listview = self.toolbar.GetListView()
        # listview.SetFont(wx.Font(wx.FontInfo(10.5)))
        # listview.SetForegroundColour(get_theme('toolbar_fg'))
        # listview.SetBackgroundColour(get_theme('toolbar_bg'))
        # listview.SetSize(100, 200)
        self.toolbar.SetForegroundColour(get_theme('toolbar_fg'))
        self.toolbar.SetBackgroundColour(get_theme('toolbar_bg'))
        self.toolbar.SetTabAreaColour(get_theme('toolbar_bg'))
        self.toolbar.SetNonActiveTabTextColour(get_theme('toolbar_fg'))
        self.toolbar.SetActiveTabTextColour(get_theme('active_tab_fg'))
        # self.toolbar.SetActiveTabColour(get_theme('active_tab_bg'))

        self.edit_panel = EditPanel(self, self.canvas, self.controller,
                                    size=(get_theme('edit_panel_width'),
                                          get_theme('canvas_height')))

        # and create a sizer to manage the layout of child widgets
        sizer = wx.GridBagSizer(vgap=get_theme('vgap'), hgap=get_theme('hgap'))

        sizer.Add(self.toolbar, wx.GBPosition(0, 0), wx.GBSpan(1, 3), flag=wx.EXPAND)
        sizer.Add(self.mode_panel, wx.GBPosition(1, 0), flag=wx.EXPAND)
        sizer.Add(self.canvas, wx.GBPosition(1, 1),  flag=wx.EXPAND)
        sizer.Add(self.edit_panel, wx.GBPosition(1, 2), wx.GBSpan(2, 1), flag=wx.EXPAND)
        sizer.Add(self.bottom_bar, wx.GBPosition(2, 0), wx.GBSpan(1, 2), flag=wx.EXPAND)

        # allow the canvas to grow
        sizer.AddGrowableCol(1, 1)
        sizer.AddGrowableRow(1, 1)

        # Set the sizer and *prevent the user from resizing it to a smaller size
        self.SetSizerAndFit(sizer)

        self.last_save_path = None

    def ToggleEditPanel(self):
        sizer = self.GetSizer()
        if self.edit_panel.IsShown():
            sizer.Detach(self.edit_panel)
            sizer.SetItemSpan(self.canvas, wx.GBSpan(1, 2))
            self.edit_panel.Hide()
        else:
            sizer.SetItemSpan(self.canvas, wx.GBSpan(1, 1))
            sizer.Add(self.edit_panel, wx.GBPosition(1, 2), flag=wx.EXPAND)
            self.edit_panel.Show()

        self.Layout()


class NetworkPrintout(wx.Printout):
    def __init__(self, img: wx.Image):
        super().__init__()
        self.image = img

    def OnPrintPage(self, pageNum: int):
        if pageNum > 1:
            return False

        self.FitThisSizeToPage(self.image.GetSize())
        dc = self.GetDC()
        assert dc.CanDrawBitmap()
        dc.DrawBitmap(wx.Bitmap(self.image), wx.Point(0, 0))

        return True


class MainFrame(wx.Frame):
    """The main frame."""
    # save_item: wx.MenuItem

    def __init__(self, controller: IController, **kw):
        super().__init__(None, style=wx.DEFAULT_FRAME_STYLE |
                         wx.WS_EX_PROCESS_UI_UPDATES, **kw)
        self.last_save_path = None
        manager = PluginManager(self, controller)
        load_theme_settings()
        self.appSettings = AppSettings()
        self.appSettings.load_appSettings()

        self.manager = manager
        status_fields = get_setting('status_fields')
        assert status_fields is not None
        self.CreateStatusBar(len(get_setting('status_fields')))
        self.SetStatusWidths([width for _, width in status_fields])
        self.main_panel = MainPanel(self, controller, manager)
        self.manager.bind_error_callback(lambda msg: self.main_panel.canvas.ShowWarningDialog(msg, caption='Plugin Error'))
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.main_panel, 1, wx.EXPAND)
        self.Bind(wx.EVT_SHOW, self.OnShow)

        canvas = self.main_panel.canvas
        self.controller = controller
        self.canvas = canvas

        def add_item(menu: wx.Menu, menu_name, callback):
            id_ = menu.Append(-1, menu_name).Id
            menu.Bind(wx.EVT_MENU, lambda _: callback(), id=id_)

        entries = list()
        menu_bar = wx.MenuBar()

        self.menu_events = list()
        file_menu = wx.Menu()

        self.AddMenuItem(file_menu, '&New', 'Start a new network',
                         lambda _: self.NewNetwork(),  entries, key=(wx.ACCEL_CTRL, ord('N')))
        file_menu.AppendSeparator()
        self.AddMenuItem(file_menu, '&Load...', 'Load network from JSON file',
                         lambda _: self.LoadFromJson(), entries, key=(wx.ACCEL_CTRL, ord('O')))
        # TODO Load Recent...
        file_menu.AppendSeparator()
        self.save_item = self.AddMenuItem(file_menu, '&Save', 'Save current network as a JSON file',
                                          lambda _: self.SaveJson(), entries, key=(wx.ACCEL_CTRL, ord('S')))
        self.save_item.Enable(False)
        self.AddMenuItem(file_menu, '&Save As...', 'Save current network as a JSON file',
                         lambda _: self.SaveAsJson(), entries, key=(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('N')))
        file_menu.AppendSeparator()
        self.AddMenuItem(file_menu, '&Edit Settings', 'Edit settings',
                         lambda _: self.EditSettings(),  entries)
        self.AddMenuItem(file_menu, '&Reload Settings', 'Reload settings',
                         lambda _: self.ReloadSettings(),  entries)
        file_menu.AppendSeparator()
        align_menu = wx.Menu()
        add_item(align_menu, 'Export .png...',
            lambda: self.ExportAs(wx.BITMAP_TYPE_PNG, 'PNG', 'PNG files (.png)|*.png'))
        add_item(align_menu, 'Export .jpg...',
            lambda: self.ExportAs(wx.BITMAP_TYPE_JPEG, 'JPEG', 'JPEG files (.jpg)|*.jpg'))
        add_item(align_menu, 'Export .bmp...',
            lambda: self.ExportAs(wx.BITMAP_TYPE_BMP, 'BMP', 'BMP files (.bmp)|*.bmp'))
        file_menu.AppendSubMenu(align_menu, '&Export As...')
        file_menu.AppendSeparator()
        self.AddMenuItem(file_menu, '&Print...', 'Print Network',
                         lambda _: self.PrintNetwork(),  entries, key=(wx.ACCEL_CTRL, ord('P')))
        file_menu.AppendSeparator()
        self.AddMenuItem(file_menu, 'E&xit', 'Exit application',
                         lambda _: self.Close(), entries,  id_=wx.ID_EXIT)

        edit_menu = wx.Menu()
        self.AddMenuItem(edit_menu, '&Undo', 'Undo action', lambda _: controller.undo(),
                         entries, key=(wx.ACCEL_CTRL, ord('Z')))
        self.AddMenuItem(edit_menu, '&Redo', 'Redo action', lambda _: controller.redo(),
                         entries, key=(wx.ACCEL_CTRL, ord('Y')))
        edit_menu.AppendSeparator()
        self.AddMenuItem(edit_menu, '&Copy', 'Copy selected nodes', lambda _: canvas.CopySelected(),
                         entries, key=(wx.ACCEL_CTRL, ord('C')))
        self.AddMenuItem(edit_menu, '&Paste', 'Paste selected nodes',
                         lambda _: canvas.Paste(), entries, key=(wx.ACCEL_CTRL, ord('V')))
        self.AddMenuItem(edit_menu, '&Cut', 'Cut selected nodes',
                         lambda _: canvas.CutSelected(), entries, key=(wx.ACCEL_CTRL, ord('X')))
        edit_menu.AppendSeparator()
        self.AddMenuItem(edit_menu, '&Delete selected', 'Deleted selected',
                         lambda _: canvas.DeleteSelectedItems(), entries,
                         key=(wx.ACCEL_NORMAL, wx.WXK_DELETE))

        select_menu = wx.Menu()
        self.AddMenuItem(select_menu, 'Select &All', 'Select all',
                         lambda _: canvas.SelectAll(), entries, key=(wx.ACCEL_CTRL, ord('A')))
        self.AddMenuItem(select_menu, 'Select All &Nodes', 'Select all nodes',
                         lambda _: canvas.SelectAllNodes(), entries, key=(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('N')))
        self.AddMenuItem(select_menu, 'Select All &Reactions', 'Select all reactions',
                         lambda _: canvas.SelectAllReactions(), entries, key=(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('R')))
        self.AddMenuItem(select_menu, 'Clear Selection', 'Clear the current selection',
                         lambda _: canvas.ClearCurrentSelection(), entries,
                         key=(wx.ACCEL_NORMAL, wx.WXK_ESCAPE))

        view_menu = wx.Menu()
        self.AddMenuItem(view_menu, 'Zoom &In', 'Zoom in canvas', lambda _: canvas.ZoomCenter(True),
                         entries, key=(wx.ACCEL_CTRL, ord('+')))
        self.AddMenuItem(view_menu, 'Zoom &Out', 'Zoom out canvas',
                         lambda _: canvas.ZoomCenter(False), entries, key=(wx.ACCEL_CTRL, ord('-')))
        self.AddMenuItem(view_menu, '&Reset Zoom', 'Reset canva zoom',
                         lambda _: canvas.ResetZoom(), entries, key=(wx.ACCEL_CTRL, ord(' ')))

        canvas_menu = wx.Menu()
        self.AddMenuItem(canvas_menu, '&Fit all node size to text',
                         'Fit the size of every node to its containing text',
                         lambda _: canvas.FitNodeSizeToText(), entries,
                         key=(wx.ACCEL_ALT | wx.ACCEL_SHIFT, ord('F')))

        reaction_menu = wx.Menu()
        self.AddMenuItem(reaction_menu, 'Mark Selected as &Reactants',
                         'Mark selected nodes as reactants',
                         lambda _: canvas.MarkSelectedAsReactants(), entries,
                         key=(wx.ACCEL_NORMAL, ord('S')))
        self.AddMenuItem(reaction_menu, 'Mark Selected as &Products',
                         'Mark selected nodes as products',
                         lambda _: canvas.MarkSelectedAsProducts(), entries,
                         key=(wx.ACCEL_NORMAL, ord('F')))
        self.AddMenuItem(reaction_menu, '&Create Reaction From Selected',
                         'Create reaction from selected sources and targets',
                         lambda _: canvas.CreateReactionFromMarked(), entries,
                         key=(wx.ACCEL_CTRL, ord('R')))

        self.plugins_menu = wx.Menu()
        self.AddMenuItem(self.plugins_menu, '&Plugins...', 'Manage plugins', self.ManagePlugins, entries,
                         key=(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('P')))
        self.AddMenuItem(self.plugins_menu, 'Add Plugins', 'Add A Plugin', self.AddPlugins, entries)
        # load the plugin items in OnShow
        self.plugins_menu.AppendSeparator()

        help_menu = wx.Menu()
        self.AddMenuItem(help_menu, '&About...',
                         'Show about dialog', self.onAboutDlg, entries)  # self.ShowAbout, entries)
        self.AddMenuItem(help_menu, '&Default settings...', 'Viewer default settings',
                         lambda _: self.ShowDefaultSettings(), entries)

        menu_bar.Append(file_menu, '&File')
        menu_bar.Append(edit_menu, '&Edit')
        menu_bar.Append(select_menu, '&Select')
        menu_bar.Append(view_menu, '&View')
        menu_bar.Append(canvas_menu, '&Canvas')
        menu_bar.Append(reaction_menu, '&Reaction')
        menu_bar.Append(self.plugins_menu, '&Plugins')
        menu_bar.Append(help_menu, '&Help')

        atable = wx.AcceleratorTable(entries)

        self.SetMenuBar(menu_bar)
        self.atable = atable
        canvas.SetAcceleratorTable(atable)

        self.OverrideAccelTable(self)

        self.Bind(wx.EVT_CLOSE, self.OnCloseExit)

        # set sizer at the end, after adding the menus.
        self.SetSizerAndFit(sizer)

        self.SetSize(self.appSettings.size)
        self.SetPosition(self.appSettings.position)
        self.Layout()

        # Record the initial position of the window
        self.controller.set_application_position(self.GetPosition())

    def OnShow(self, evt):
        if runtime_vars().enable_plugins:
            self.manager.load_from('rkviewer_plugins')
            self.manager.register_menu(self.plugins_menu)
            self.main_panel.toolbar.AddPluginPages()
        evt.Skip()

    # Anything we need to do when the app closes can be included here
    def OnCloseExit(self, evt):
        self.appSettings.size = self.GetSize()
        self.appSettings.position = self.Position
        self.appSettings.save_appSettings()
        self.Destroy()

    def AddMenuItem(self, menu: wx.Menu, text: str, help_text: str, callback: Callable,
                    entries: List, key: Tuple[Any, int] = None, id_: int = None) -> wx.MenuItem:
        if id_ is None:
            id_ = wx.NewIdRef(count=1)

        shortcut = ''
        if key is not None:
            entry = wx.AcceleratorEntry(key[0], key[1], id_)
            entries.append(entry)
            shortcut = entry.ToString()

        item = menu.Append(id_, '{}\t{}'.format(text, shortcut), help_text)
        self.Bind(wx.EVT_MENU, callback, item)
        self.menu_events.append((callback, item))
        return item

    def onAboutDlg(self, event):
        info = wx.adv.AboutDialogInfo()
        info.SetName("SBcoyote")
        info.SetVersion("1.0.0")
        info.SetCopyright("(c) 2023 UW Sauro Lab")
        info.SetDescription("An Extensible Reaction Network Editor")
        info.SetWebSite("https://github.com/sys-bio/SBcoyote",
                        "Home Page")  # TODO update home page?
        info.SetDevelopers(["Gary Geng", "Jin Xu", "Nhan D. Nguyen", "Carmen Pereña Cortés","Claire Samuels", "Herbert Sauro"])# TODO update authors
        info.SetLicense("MIT")

        # Show the wx.AboutBox
        wx.adv.AboutBox(info)

    def ReloadSettings(self):
        load_theme_settings()
        err = pop_settings_err()
        if err is None:
            # msg = NotificationMessage('Settings reloaded', 'Some changes may not be applied until the application is restarted.')
            # msg.Show()
            pass
        else:
            if isinstance(err, JSONLibraryException):
                message = 'Failed when parsing settings.json.\n\n'
                message += err.message
            else:
                message = 'Invalid settings in settings.json.\n\n'
                message += str(err)
            message += str(err)
            self.main_panel.canvas.ShowWarningDialog(message)

    def EditSettings(self):
        """Open the preferences file for editing."""
        if not self.CreateConfigDir(GetConfigDir()):
            return

        if not os.path.exists(GetThemeSettingsPath()):
            with open(GetThemeSettingsPath(), 'w') as fp:
                fp.write(INIT_SETTING_TEXT)
        else:
            if not os.path.isfile(GetThemeSettingsPath()):
                self.main_panel.canvas.ShowWarningDialog('Could not open settings file since '
                                                         'a directory already exists at path '
                                                         '{}.'.format(GetThemeSettingsPath()))
                return

        # If we're running windows use notepad
        if os.name == 'nt':
            # Doing it this way allows python to regain control even though notepad hasn't been clsoed
            import subprocess
            _pid = subprocess.Popen(['notepad.exe', GetThemeSettingsPath()]).pid
        else:
            start_file(GetThemeSettingsPath())

    def CreateConfigDir(self, config_dir: str):
        """Create the configuration directory if it does not already exist."""
        try:
            sp = wx.StandardPaths.Get()
            config_dir = sp.GetUserConfigDir()
            if not os.path.exists(os.path.join(config_dir, 'rkViewer')):
                config_dir = os.path.join(config_dir, 'rkViewer')
                Path(config_dir).mkdir(parents=True, exist_ok=True)
            else:
                config_dir = os.path.join(os.path.join(config_dir, 'rkViewer'))
            return True
        except FileExistsError:
            # TODO fix
            self.main_panel.canvas.ShowWarningDialog('Could not create RKViewer configuration '
                                                     'directory. A file already exists at path '
                                                     '{}.'.format(config_dir))
        return False

    def ShowDefaultSettings(self):
        if not self.CreateConfigDir(GetConfigDir()):
            return

        if os.path.exists(os.path.join(GetConfigDir(), 'rkViewer', '.default-settings.json')) and \
            not os.path.isfile(os.path.join(GetConfigDir(), 'rkViewer', '.default-settings.json')):
            self.main_panel.canvas.ShowWarningDialog('Could not open default settings file '
                                                     'since a directory already exists at path '
                                                     '{}.'.format(os.path.join(GetConfigDir(),
                                                     'rkViewer', '.default-settings.json')))
            return
        # TODO prepopulate file with help text, i.e link to docs about schema
        json_str = json.dumps(get_default_raw_settings(), indent=4, sort_keys=True)
        with open(os.path.join(GetConfigDir(), 'rkViewer', '.default-settings.json'), 'w') as fp:
            fp.write(DEFAULT_SETTING_FMT.format(json_str))

        # If we're running windows use notepad
        if os.name == 'nt':
            # Doing it this way allows python to regain control even though notepad hasn't been clsoed
            import subprocess
            _pid = subprocess.Popen(['notepad.exe', os.path.join(
                GetConfigDir(), 'rkViewer', '.default-settings.json')]).pid
        else:
            start_file(os.path.join(GetConfigDir(), '.default-settings.json'))

    def NewNetwork(self):
        self.save_item.Enable()
        self.controller.new_network()

    def PrintNetwork(self):
        img = self._GetExportImage()
        if not img:
            return

        # Pass two printout objects: for preview, and possible printing.
        printer = wx.Printer()
        printout = NetworkPrintout(img)
        printer.Print(self, printout, True)

    def ExportNetwork(self):
        self.main_panel.canvas.ShowWarningDialog("Export not yet implemented")

    def _GetExportImage(self) -> Optional[wx.Image]:
        img = self.main_panel.canvas.DrawActiveRectToImage()
        if img is None:
            self.canvas.ShowWarningDialog(
                'There are no relevant elements (nodes/reactions/compartments) on the canvas! Print aborted.')
            return None
        return img

    def ExportAs(self, btype, type_name: str, wildcard: str):
        """Export as the type given by btype (wx.BitmapType). btype is passed to SaveFile()
        """
        img = self._GetExportImage()
        if img is None:
            return

        with wx.FileDialog(self, "Save {} file".format(type_name), wildcard=wildcard,
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return  # the user changed their mind
            pathname = fileDialog.GetPath()
            try:
                net_index = 0
                net_json = self.controller.dump_network(net_index)
                with open(pathname, 'w') as file:
                    json.dump(net_json, file, sort_keys=True, indent=4)

                # Allow Save action, since we now know where to save to
                self.last_save_path = pathname
                self.save_item.Enable()
            except IOError:
                wx.LogError("Cannot save current data in file '{}'.".format(pathname))
            img.SaveFile(pathname, type=btype)

    def SaveJson(self):
        if self.last_save_path is None:
            return self.SaveAsJson()
        try:
            net_index = 0
            net_json = self.controller.dump_network(net_index)
            with open(self.last_save_path, 'w') as file:
                json.dump(net_json, file, sort_keys=True, indent=4)
        except IOError:
            wx.LogError("Cannot save current data in file '{}'.".format(self.last_save_path))

    def SaveAsJson(self):
        with wx.FileDialog(self, "Save JSON file", wildcard="JSON files (*.json)|*.json",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return  # the user changed their mind

            # save the current contents in the file
            pathname = fileDialog.GetPath()
            try:
                net_index = 0
                net_json = self.controller.dump_network(net_index)
                with open(pathname, 'w') as file:
                    json.dump(net_json, file, sort_keys=True, indent=4)

                # Allow Save action, since we now know where to save to
                self.last_save_path = pathname
                self.save_item.Enable()
            except IOError:
                wx.LogError("Cannot save current data in file '{}'.".format(pathname))

    def LoadFromJson(self):
        with wx.FileDialog(self, "Load JSON file", wildcard="JSON files (*.json)|*.json",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return  # the user changed their mind

            # save the current contents in the file
            pathname = fileDialog.GetPath()
            try:
                with open(pathname, 'r') as file:
                    try:
                        net_json = json.load(file)
                    except:
                        wx.LogError("Cannot load network from the file!")
                        #wx.MessageBox("Unable to open the clipboard", "Error")
                try:
                    _net_index = self.controller.load_network(net_json)
                except:
                    wx.LogError("Cannot load network from the file!")
            except IOError:
                wx.LogError("Cannot load network from file '{}'.".format(pathname))

    def ManagePlugins(self, evt):
        # TODO create special empty page that says "No plugins loaded"
        with self.manager.create_dialog(self) as dlg:
            dlg.Centre()
            if dlg.ShowModal() == wx.ID_OK:
                pass  # exited normally
            else:
                pass  # exited by clicking some button

    def AddPlugins(self, evt):
        with self.manager.create_install_dialog(self) as dlg:
            dlg.Centre()
            if not dlg.ShowModal() == wx.ID_OK:
                sep_idx = -1
                for idx, item in enumerate(self.plugins_menu.GetMenuItems()):
                    if sep_idx < 0 and item.IsSeparator():
                        sep_idx = idx
                    if sep_idx >= 0 and idx > sep_idx:
                        self.plugins_menu.Remove(item)
                self.manager.plugins = list()
                self.manager.load_from('rkviewer_plugins')
                self.manager.register_menu(self.plugins_menu)
                self.main_panel.toolbar.UpdatePluginPages()

    def OverrideAccelTable(self, widget):
        """Set up functions to disable accelerator shortcuts for certain descendants of widgets.

        This is to prevent accelerator shortcuts to be applied in unexpected situations, when
        something other than the canvas is in foucs. For example, if the user is editing the name
        of a node, they may use ctrl+Z to undo some text operation. However, since ctrl+Z is bound
        to the "undo last operation" action on canvas, it will be caught by the canvas instead.
        This prevents that by attaching a temporary, "null" accelerator table when a TextCtrl
        widget goes into focus.
        """
        if isinstance(widget, wx.TextCtrl):
            def OnFocus(evt):
                # for cb, item in self.menu_events:
                #     self.Unbind(wx.EVT_MENU, handler=cb, source=item)

                # For some reason, we need to do this for both self and menubar to disable the
                # AcceleratorTable. Don't ever lose this sacred knowledge, for it came at the cost
                # of 50 minutes.
                self.SetAcceleratorTable(wx.NullAcceleratorTable)
                self.GetMenuBar().SetAcceleratorTable(wx.NullAcceleratorTable)
                evt.Skip()

            def OnUnfocus(evt):
                # for cb, item in self.menu_events:
                #     self.Bind(wx.EVT_MENU, handler=cb, source=item)
                self.SetAcceleratorTable(self.atable)
                evt.Skip()

            widget.Bind(wx.EVT_SET_FOCUS, OnFocus)
            widget.Bind(wx.EVT_KILL_FOCUS, OnUnfocus)

        for child in widget.GetChildren():
            self.OverrideAccelTable(child)


class RKView(IView):
    """Implementation of the view class."""
    def __init__(self):
        self.controller = None
        self.manager = None
        self.app = None

    def bind_controller(self, controller: IController):
        self.controller = controller

    def init(self):
        assert self.controller is not None
        self.app = wx.App()
        self.frame = MainFrame(self.controller, title='SBcoyote')
        init_api(self.frame.main_panel.canvas, self.controller)
        self.canvas_panel = self.frame.main_panel.canvas

    def main_loop(self):
        assert self.app is not None
        self.frame.Show()
        self.app.MainLoop()

    def update_all(self, nodes: List[Node], reactions: List[Reaction],
                   compartments: List[Compartment]):
        """Update the list of nodes.

        Note that RKView takes ownership of the list of nodes and may modify it.
        """
        self.canvas_panel.Reset(nodes, reactions, compartments)
