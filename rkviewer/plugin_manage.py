"""Classes for managing plugins for Canvas."""
# pylint: disable=maybe-no-member
import importlib.abc
import importlib.util
import inspect
import os
import sys
from typing import Any, Callable, List, Optional, cast

# pylint: disable=no-name-in-module
import wx
from rkplugin.plugins import CommandPlugin, Plugin, PluginType, WindowedPlugin
# pylint: disable=no-name-in-module
from wx.html import HtmlWindow

from rkviewer.events import (CanvasEvent, DidAddCompartmentEvent,
                             DidAddNodeEvent, DidAddReactionEvent, DidChangeCompartmentOfNodesEvent,
                             DidCommitDragEvent, DidDeleteEvent,
                             DidModifyCompartmentsEvent, DidModifyNodesEvent,
                             DidModifyReactionEvent, DidMoveBezierHandleEvent,
                             DidMoveNodesEvent, DidPaintCanvasEvent,
                             DidRedoEvent, DidResizeCompartmentsEvent,
                             DidResizeNodesEvent, DidUndoEvent,
                             SelectionDidUpdateEvent, bind_handler)
from rkviewer.mvc import IController


class PluginManager:
    plugins: List[Plugin]

    def __init__(self, controller: IController):
        self.plugins = list()
        self.controller = controller
        bind_handler(DidAddNodeEvent, self.make_notify('on_did_add_node'))
        bind_handler(DidMoveNodesEvent, self.make_notify('on_did_move_nodes'))
        bind_handler(DidResizeNodesEvent, self.make_notify('on_did_resize_nodes'))
        bind_handler(DidAddCompartmentEvent, self.make_notify('on_did_add_compartment'))
        bind_handler(DidResizeCompartmentsEvent, self.make_notify('on_did_resize_compartments'))
        bind_handler(DidAddReactionEvent, self.make_notify('on_did_add_reaction'))
        bind_handler(DidUndoEvent, self.make_notify('on_did_undo'))
        bind_handler(DidRedoEvent, self.make_notify('on_did_redo'))
        bind_handler(DidDeleteEvent, self.make_notify('on_did_delete'))
        bind_handler(DidCommitDragEvent, self.make_notify('on_did_commit_drag'))
        bind_handler(DidPaintCanvasEvent, self.make_notify('on_did_paint_canvas'))
        bind_handler(SelectionDidUpdateEvent, self.make_notify('on_selection_did_change'))
        bind_handler(DidMoveBezierHandleEvent, self.make_notify('on_did_move_bezier_handle'))
        bind_handler(DidModifyNodesEvent, self.make_notify('on_did_modify_nodes'))
        bind_handler(DidModifyReactionEvent, self.make_notify('on_did_modify_reactions'))
        bind_handler(DidModifyCompartmentsEvent, self.make_notify('on_did_modify_compartments'))
        bind_handler(DidChangeCompartmentOfNodesEvent,
                     self.make_notify('on_did_change_compartment_of_nodes'))

    # Also TODO might want a more sophisticated file system structure, including data storage and
    # temp folder
    def load_from(self, dir_path: str) -> bool:
        """Load plugins from the given directory. Returns False if the dir does not exist.
        """
        if not os.path.exists(dir_path):
            return False

        plugin_classes = list()
        for f in os.listdir(dir_path):
            if not f.endswith('.py'):
                continue
            mod_name = '_rkplugin_{}'.format(f[:-2])  # remove extension
            spec = importlib.util.spec_from_file_location(mod_name, os.path.join(dir_path, f))
            mod = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            loader = cast(importlib.abc.Loader, spec.loader)
            loader.exec_module(mod)

            def pred(o): return o.__module__ == mod_name and issubclass(o, Plugin)
            cur_classes = [m[1] for m in inspect.getmembers(mod, inspect.isclass) if pred(m[1])]
            for cls in cur_classes:
                if inspect.isabstract(cls):
                    raise ValueError("In file {}, {} is an abstract class", f)
            plugin_classes += cur_classes

        self.plugins = [cls() for cls in plugin_classes]
        return True

    def make_notify(self, handler_name: str):
        """Make event notification function for plugin.

        handler_name should be the name of a method defined by Plugin. This would then create a
        callback function that goes over each plugin and call that function. This callback should
        be bound to its associated event.

        The handler function is called with the event itself as argument.
        """
        assert callable(getattr(Plugin, handler_name, None)), "{} is not a method defined by \
Plugin!".format(handler_name)

        def ret(evt: CanvasEvent):
            for plugin in self.plugins:
                getattr(plugin, handler_name)(evt)

        return ret

    def register_menu(self, menu: wx.Menu, parent: wx.Window):
        commands = [cast(CommandPlugin, p) for p in self.plugins if p.ptype == PluginType.COMMAND]
        windowed = [cast(WindowedPlugin, p) for p in self.plugins if p.ptype == PluginType.WINDOWED]

        if len(self.plugins) != 0:
            menu.AppendSeparator()

        for plugin in commands:
            id_ = wx.NewIdRef(count=1)
            item = menu.Append(id_, plugin.metadata.name)
            menu.Bind(wx.EVT_MENU, self.make_command_callback(plugin), item)

        if len(commands) != 0 and len(windowed) != 0:
            menu.AppendSeparator()

        for plugin in windowed:
            id_ = wx.NewIdRef(count=1)
            item = menu.Append(id_, plugin.metadata.name)
            menu.Bind(wx.EVT_MENU, self.make_windowed_callback(plugin, parent), item)

    def make_command_callback(self, command: CommandPlugin) -> Callable[[Any], None]:
        def command_cb(_):
            self.controller.start_group()
            command.run()
            self.controller.end_group()

        return command_cb

    def make_windowed_callback(self, windowed: WindowedPlugin,
                               parent: wx.Window) -> Callable[[Any], None]:
        title = windowed.metadata.name
        dialog_exists = False
        dialog: Optional[wx.Window] = None

        def windowed_cb(_):
            nonlocal dialog_exists, dialog

            if not dialog_exists:
                dialog = wx.Dialog(parent, title=title)
                dialog_exists = True
                window = windowed.create_window(dialog)
                if window is None or not isinstance(window, wx.Window):
                    raise ValueError('create_window() of plugin {} did not return wx.Window '
                                     'type!'.format(windowed.metadata.name))
                windowed.dialog = dialog  # Set the related dialog

                sizer = wx.BoxSizer(wx.VERTICAL)
                sizer.Add(window)
                dialog.SetSize(window.GetSize())
                dialog.SetSizer(sizer)
                dialog.Centre()

                windowed.on_did_create_dialog()
                dialog.Show()

                def close_cb(e):
                    nonlocal dialog_exists
                    windowed.on_will_close_window(e)
                    dialog_exists = False
                dialog.Bind(wx.EVT_CLOSE, close_cb)
            else:
                assert dialog is not None
                dialog.SetFocus()
        return windowed_cb

    def create_dialog(self, parent):
        return PluginDialog(parent, self.plugins)


class PluginDialog(wx.Dialog):
    def __init__(self, parent, plugins: List[Plugin]):
        super().__init__(parent, title='Manage Plugins', size=(900, 550))
        notebook = wx.Listbook(self, style=wx.LB_LEFT)
        notebook.GetListView().SetFont(wx.Font(wx.FontInfo(10)))
        notebook.GetListView().SetColumnWidth(0, 100)

        sizer = wx.BoxSizer()
        sizer.Add(notebook, proportion=1, flag=wx.EXPAND)

        for plugin in plugins:
            page = PluginPage(notebook, plugin)
            notebook.AddPage(page, text=plugin.metadata.name)

        self.SetSizer(sizer)


class PluginPage(HtmlWindow):
    def __init__(self, parent: wx.Window, plugin: Plugin):
        super().__init__(parent)

        html = '''
        <h3>{name}</h3>
        <div>{author}｜v{version}</div>
        <hr/>
        <div>
            {description}
        </div>
        '''.format(
            name=plugin.metadata.name,
            version=plugin.metadata.version,
            author=plugin.metadata.author,
            description=plugin.metadata.long_desc,
        )

        self.SetPage(html)
        # inherit parent background color for better look
        self.SetBackgroundColour(parent.GetBackgroundColour())

        '''
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_flags = wx.SizerFlags().Border(wx.TOP | wx.LEFT, 10)
        title = wx.StaticText(self, label=plugin.metadata.name)
        title.SetFont(wx.Font(wx.FontInfo(14).Bold()))
        sizer.Add(title, sizer_flags)
        author = wx.StaticText(self, label='{}, by {}'.format(plugin.metadata.version, plugin.metadata.author))
        author.SetFont(wx.Font(wx.FontInfo(10).Italic()))
        sizer.Add(author, sizer_flags)
        desc = wx.StaticText(self, label=plugin.metadata.long_desc)
        desc.SetFont(wx.Font(wx.FontInfo(10)))
        sizer.Add(desc, sizer_flags)
        self.SetSizer(sizer)
        '''
