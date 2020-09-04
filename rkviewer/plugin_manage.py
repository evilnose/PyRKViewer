"""Classes for managing plugins."""
# pylint: disable=maybe-no-member
from dataclasses import astuple, is_dataclass
from rkviewer.mvc import IController
import wx
import os
import importlib.abc
import importlib.util
import inspect
from rkviewer.events import DidAddNodeEvent, SelectionDidUpdateEvent, bind_handler
from typing import Any, Callable, List, cast
from rkplugin.plugins import CommandPlugin, Plugin, PluginType, WindowedPlugin


class PluginManager:
    plugins: List[Plugin]

    def __init__(self, controller: IController):
        self.plugins = list()
        self.controller = controller
        bind_handler(DidAddNodeEvent, self.make_notify('on_did_add_node'))
        bind_handler(SelectionDidUpdateEvent, self.make_notify('on_selection_did_change'))

    def load_from(self, dir_path: str):
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

        # TODO catch error
        self.plugins = [cls() for cls in plugin_classes]

    def make_notify(self, handler_name: str):
        assert callable(getattr(Plugin, handler_name, None)), "{} is not a method defined by \
Plugin!".format(handler_name)

        def ret(evt):
            # TODO error handling
            assert is_dataclass(evt), "Handler created by make_notify() must be given a \
dataclass argument."
            for plugin in self.plugins:
                getattr(plugin, handler_name)(*astuple(evt))

        return ret

    def register_menu(self, menu: wx.Menu, parent: wx.Window):
        commands = [cast(CommandPlugin, p) for p in self.plugins if p.ptype == PluginType.COMMAND]
        for plugin in commands:
            id_ = wx.NewId()
            item = menu.Append(id_, plugin.metadata.name)
            menu.Bind(wx.EVT_MENU, self.make_command_callback(plugin), item)

        windowed = [cast(WindowedPlugin, p) for p in self.plugins if p.ptype == PluginType.WINDOWED]
        for plugin in windowed:
            id_ = wx.NewId()
            item = menu.Append(id_, plugin.metadata.name)
            menu.Bind(wx.EVT_MENU, self.make_windowed_callback(plugin, parent), item)

    def make_command_callback(self, command: CommandPlugin) -> Callable[[Any], None]:
        def command_cb(_):
            self.controller.try_start_group()
            command.run()
            self.controller.try_end_group()

        return command_cb

    def make_windowed_callback(self, windowed: WindowedPlugin,
                               parent: wx.Window) -> Callable[[Any], None]:
        title = windowed.metadata.name
        dialog_exists = False
        dialog: wx.Window = None

        def windowed_cb(_):
            nonlocal dialog_exists, dialog

            if not dialog_exists:
                dialog = wx.Dialog(parent, title=title)
                dialog_exists = True
                window = windowed.create_window(dialog)
                sizer = wx.BoxSizer(wx.VERTICAL)
                sizer.Add(window)
                dialog.SetSize(window.GetSize())
                dialog.SetSizer(sizer)
                dialog.Centre()
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
        return PluginWindow(parent)


class PluginWindow(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title='Manage Plugins')
