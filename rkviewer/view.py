"""The main View class and associated widgets.
"""
from rkviewer.canvas.geometry import get_bounding_rect
import rkviewer
from rkplugin.api import init_api
from rkviewer.plugin_manage import PluginManager
# pylint: disable=maybe-no-member
import wx
import wx.lib.agw.flatnotebook as fnb
import wx.lib.agw.shortcuteditor as sedit
from typing import Callable, List, Dict, Any, Tuple
from .events import DidMoveCompartmentsEvent, DidResizeCompartmentsEvent, DidResizeNodesEvent, DidMoveNodesEvent, bind_handler, CanvasDidUpdateEvent, \
    SelectionDidUpdateEvent
from .canvas.canvas import Canvas
from .canvas.data import Compartment, Node, Reaction
from .canvas.state import cstate, InputMode
from .config import settings, theme
from .forms import CompartmentForm, NodeForm, ReactionForm
from .mvc import IController, IView
from .utils import ButtonGroup, get_path


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
    FNB_STYLE = fnb.FNB_NO_X_BUTTON | fnb.FNB_NO_NAV_BUTTONS | fnb.FNB_NODRAG | fnb.FNB_VC8 | fnb.FNB_DROPDOWN_TABS_LIST

    def __init__(self, parent, canvas: Canvas, controller: IController, **kw):
        super().__init__(parent, agwStyle=EditPanel.FNB_STYLE, **kw)

        self.canvas = canvas

        self.node_form = NodeForm(self, canvas, controller)
        self.reaction_form = ReactionForm(self, canvas, controller)
        self.comp_form = CompartmentForm(self, canvas, controller)

        self.null_message = wx.Panel(self)
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
        bind_handler(DidMoveCompartmentsEvent, self.OnNodesDidMove)
        bind_handler(DidResizeCompartmentsEvent, self.OnDidResizeNodes)

    def OnCanvasDidUpdate(self, evt):
        self.node_form.UpdateNodes(evt.nodes)
        self.reaction_form.UpdateReactions(evt.reactions)
        self.comp_form.UpdateCompartments(evt.compartments)

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
            self.comp_form.UpdateSelection(evt.compartment_indices, nodes_selected=should_show_nodes)
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

        # restore focus, since otherwise for some reason the newly added page gets the focus
        focused.SetFocus()

        # need to manually show this for some reason
        if not should_show_nodes and not should_show_reactions and not should_show_comps:
            self.null_message.Show()

    def OnNodesDidMove(self, evt):
        self.node_form.NodesMovedOrResized(evt)

    def OnCompartmentsDidMove(self, evt):
        self.comp_form.CompsMovedOrResized(evt)

    def OnDidResizeNodes(self, evt):
        self.node_form.NodesMovedOrResized(evt)

    def OnDidResizeCompartments(self, evt):
        self.comp_form.CompsMovedOrResized(evt)


class Toolbar(wx.Panel):
    """ModePanel at the top of the app."""

    def __init__(self, parent, controller: IController, zoom_callback, edit_panel_callback, **kw):
        super().__init__(parent, **kw)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        zoom_in_btn = wx.Button(self, label="Zoom In")
        # TODO make this a method
        sizerflags = wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL).Border(wx.LEFT, 10)
        undo_button = wx.Button(self, label="Undo")
        sizer.Add(undo_button, sizerflags)
        undo_button.Bind(wx.EVT_BUTTON, lambda _: controller.undo())

        redo_button = wx.Button(self, label="Redo")
        sizer.Add(redo_button, sizerflags)
        redo_button.Bind(wx.EVT_BUTTON, lambda _: controller.redo())

        sizer.Add(zoom_in_btn, sizerflags)
        zoom_in_btn.Bind(wx.EVT_BUTTON, lambda _: zoom_callback(True))

        zoom_out_btn = wx.Button(self, label="Zoom Out")
        sizer.Add(zoom_out_btn, sizerflags)
        zoom_out_btn.Bind(wx.EVT_BUTTON, lambda _: zoom_callback(False))

        # Note: Right align after this
        sizer.Add((0, 0), proportion=1, flag=wx.EXPAND)

        toggle_panel_button = wx.Button(self, label="Toggle Details")
        sizer.Add(toggle_panel_button, wx.SizerFlags().Align(
            wx.ALIGN_CENTER_VERTICAL).Border(wx.RIGHT, 10))
        toggle_panel_button.Bind(wx.EVT_BUTTON, edit_panel_callback)

        self.SetSizer(sizer)


class ModePanel(wx.Panel):
    """ModePanel at the left of the app."""

    def __init__(self, *args, toggle_callback, canvas: Canvas, **kw):
        super().__init__(*args, **kw)

        self.btn_group = ButtonGroup(toggle_callback)

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.AppendModeButton('Select', InputMode.SELECT, sizer)
        self.AppendModeButton('+Nodes', InputMode.ADD_NODES, sizer)
        self.AppendModeButton('+Compts', InputMode.ADD_COMPARTMENTS, sizer)
        self.AppendModeButton('Zoom', InputMode.ZOOM, sizer)

        self.AppendSeparator(sizer)
        self.AppendNormalButton('Reactants', canvas.MarkSelectedAsReactants,
                                sizer, tooltip='Mark selected nodes as reactants')
        self.AppendNormalButton('Products', canvas.MarkSelectedAsProducts,
                                sizer, tooltip='Mark selected nodes as products')
        self.AppendNormalButton('Create Rxn', canvas.CreateReactionFromMarked,
                                sizer, tooltip='Create reaction from marked reactants and products')

        self.SetSizer(sizer)

    def AppendModeButton(self, label: str, mode: InputMode, sizer: wx.Sizer):
        btn = wx.ToggleButton(self, label=label)
        sizer.Add(btn, wx.SizerFlags().Align(
            wx.ALIGN_CENTER).Border(wx.TOP, 10))
        self.btn_group.AddButton(btn, mode)

    def AppendNormalButton(self, label: str, callback, sizer: wx.Sizer, tooltip: str = None):
        btn = wx.Button(self, label=label)
        if tooltip is not None:
            btn.SetToolTip(tooltip)
        btn.Bind(wx.EVT_BUTTON, lambda _: callback())
        sizer.Add(btn, wx.SizerFlags().Align(
            wx.ALIGN_CENTER).Border(wx.TOP, 10))

    def AppendSeparator(self, sizer: wx.Sizer):
        line = wx.StaticLine(self, style=wx.LI_HORIZONTAL)
        sizer.Add(line, wx.SizerFlags().Expand().Border(wx.TOP, 10))


class MainPanel(wx.Panel):
    """The main panel, which is the only chlid of the root Frame."""
    controller: IController
    theme: Dict[str, Any]
    canvas: Canvas
    mode_panel: ModePanel
    toolbar: Toolbar
    edit_panel: EditPanel

    def __init__(self, parent, controller: IController):
        # ensure the parent's __init__ is called
        super().__init__(parent, style=wx.CLIP_CHILDREN)
        self.SetBackgroundColour(theme['overall_bg'])
        self.controller = controller

        self.canvas = Canvas(self.controller, self,
                             size=(theme['canvas_width'],
                                   theme['canvas_height']),
                             realsize=(4 * theme['canvas_width'],
                                       4 * theme['canvas_height']),
                             )
        init_api(self.canvas, controller)
        self.canvas.SetScrollRate(10, 10)

        # The bg of the available canvas will be drawn by canvas in OnPaint()
        self.canvas.SetBackgroundColour(theme['canvas_outside_bg'])

        def set_input_mode(ident): cstate.input_mode = ident

        # create a panel in the frame
        self.mode_panel = ModePanel(self,
                                    size=(theme['mode_panel_width'],
                                          theme['canvas_height']),
                                    toggle_callback=set_input_mode,
                                    canvas=self.canvas,
                                    )
        self.mode_panel.SetBackgroundColour(theme['toolbar_bg'])

        toolbar_width = theme['canvas_width'] + \
            theme['edit_panel_width'] + theme['vgap']
        self.toolbar = Toolbar(self, controller,
                               size=(toolbar_width, theme['toolbar_height']),
                               zoom_callback=self.canvas.ZoomCenter,
                               edit_panel_callback=self.ToggleEditPanel)
        self.toolbar.SetBackgroundColour(theme['toolbar_bg'])

        self.edit_panel = EditPanel(self, self.canvas, self.controller,
                                    size=(theme['edit_panel_width'],
                                          theme['canvas_height']))
        self.edit_panel.SetBackgroundColour(theme['toolbar_bg'])

        # and create a sizer to manage the layout of child widgets
        sizer = wx.GridBagSizer(vgap=theme['vgap'], hgap=theme['hgap'])

        sizer.Add(self.toolbar, wx.GBPosition(0, 1),
                  wx.GBSpan(1, 2), flag=wx.EXPAND)
        sizer.Add(self.mode_panel, wx.GBPosition(1, 0), flag=wx.EXPAND)
        sizer.Add(self.canvas, wx.GBPosition(1, 1),  flag=wx.EXPAND)
        sizer.Add(self.edit_panel, wx.GBPosition(1, 2), flag=wx.EXPAND)

        # allow the canvas to grow
        sizer.AddGrowableCol(1, 1)
        sizer.AddGrowableRow(1, 1)

        # Set the sizer and *prevent the user from resizing it to a smaller size
        self.SetSizerAndFit(sizer)

    def ToggleEditPanel(self, evt):
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


class AboutDialog(wx.Dialog):
    def __init__(self, parent: wx.Window):
        super().__init__(parent, title='About RKViewer')
        sizer = wx.FlexGridSizer(cols=2, vgap=5, hgap=5)
        self.left_width = 150
        self.right_width = 180
        self.row_height = 50
        self.leftflags = wx.SizerFlags().Border(wx.TOP, 10)
        self.rightflags = wx.SizerFlags().Border(wx.TOP, 10)
        self.leftfont = wx.Font(wx.FontInfo(10).Bold())
        self.rightfont = wx.Font(wx.FontInfo(10))
        self.AppendRow('version', rkviewer.__version__, sizer)
        self.SetSizerAndFit(sizer)

    def AppendRow(self, left_text: str, right_text: str, sizer: wx.FlexGridSizer):
        left = wx.StaticText(self, label=left_text, size=(self.left_width, 30),
                             style=wx.ALIGN_RIGHT)
        left.SetFont(self.leftfont)
        right = wx.StaticText(self, label=right_text, size=(self.right_width, 30),
                              style=wx.ALIGN_LEFT)
        right.SetFont(self.rightfont)
        sizer.Add(left, self.leftflags)
        sizer.Add(right, self.rightflags)


class MainFrame(wx.Frame):
    """The main frame."""

    def __init__(self, controller: IController, manager: PluginManager, **kw):
        super().__init__(None, style=wx.DEFAULT_FRAME_STYLE |
                         wx.WS_EX_PROCESS_UI_UPDATES, **kw)

        self.manager = manager
        status_fields = settings['status_fields']
        assert status_fields is not None
        self.CreateStatusBar(len(settings['status_fields']))
        self.SetStatusWidths([width for _, width in status_fields])
        self.main_panel = MainPanel(self, controller)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.main_panel, 1, wx.EXPAND)

        canvas = self.main_panel.canvas

        entries = list()
        menu_bar = wx.MenuBar()

        self.menu_events = list()
        file_menu = wx.Menu()
        self.AddMenuItem(file_menu, 'E&xit', 'Exit application', lambda _: self.Close(), entries,
                         id_=wx.ID_EXIT)

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

        plugins_menu = wx.Menu()
        self.AddMenuItem(plugins_menu, '&Plugins...', 'Manage plugins', self.ManagePlugins, entries,
                         key=(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('P')))
        self.manager.register_menu(plugins_menu, self)

        help_menu = wx.Menu()
        self.AddMenuItem(help_menu, '&About...',
                         'Show about dialog', self.ShowAbout, entries)

        menu_bar.Append(file_menu, '&File')
        menu_bar.Append(edit_menu, '&Edit')
        menu_bar.Append(select_menu, '&Select')
        menu_bar.Append(view_menu, '&View')
        menu_bar.Append(reaction_menu, '&Reaction')
        menu_bar.Append(plugins_menu, '&Plugins')
        menu_bar.Append(help_menu, '&Help')

        atable = wx.AcceleratorTable(entries)

        self.SetMenuBar(menu_bar)
        self.atable = atable
        canvas.SetAcceleratorTable(atable)

        self.OverrideAccelTable(self)

        # set sizer at the end, after adding the menus.
        self.SetSizerAndFit(sizer)
        self.Center()

    def AddMenuItem(self, menu: wx.Menu, text: str, help_text: str, callback: Callable,
                    entries: List, key: Tuple[Any, int] = None, id_: int = None):
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

    def ManagePlugins(self, evt):
        # TODO create special empty page that says "No plugins loaded"
        with self.manager.create_dialog(self) as dlg:
            dlg.Centre()
            if dlg.ShowModal() == wx.ID_OK:
                pass  # exited normally
            else:
                pass  # exited by clicking some button

    def ShowAbout(self, evt):
        with AboutDialog(self) as dlg:
            dlg.Centre()
            dlg.ShowModal()

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
                for cb, item in self.menu_events:
                    self.Unbind(wx.EVT_MENU, handler=cb, source=item)
                # For some reason, we need to do this for both self and menubar to disable the
                # AcceleratorTable. Don't ever lose this sacred knowledge, for it came at the cost
                # of 50 minutes.
                self.SetAcceleratorTable(wx.NullAcceleratorTable)
                self.GetMenuBar().SetAcceleratorTable(wx.NullAcceleratorTable)
                evt.Skip()

            def OnUnfocus(evt):
                for cb, item in self.menu_events:
                    self.Bind(wx.EVT_MENU, handler=cb, source=item)
                self.SetAcceleratorTable(self.atable)
                evt.Skip()

            widget.Bind(wx.EVT_SET_FOCUS, OnFocus)
            widget.Bind(wx.EVT_KILL_FOCUS, OnUnfocus)

        for child in widget.GetChildren():
            self.OverrideAccelTable(child)


class View(IView):
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
        self.manager = PluginManager(self.controller)
        self.manager.load_from('plugins')
        self.frame = MainFrame(
            self.controller, self.manager, title='RK Network Viewer')
        self.canvas_panel = self.frame.main_panel.canvas

    def main_loop(self):
        assert self.app is not None
        self.frame.Show()
        self.app.MainLoop()

    def update_all(self, nodes: List[Node], reactions: List[Reaction],
                   compartments: List[Compartment]):
        """Update the list of nodes.

        Note that View takes ownership of the list of nodes and may modify it.
        """
        self.canvas_panel.Reset(nodes, reactions, compartments)
        self.canvas_panel.LazyRefresh()
