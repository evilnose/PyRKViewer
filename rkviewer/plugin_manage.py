"""Classes for managing plugins for Canvas.

Note: This file imports stuff from rkviewer.plugin.classes, but usually rkviewer.plugin imports from
rkviewer. Beware of circular dependency.
"""
# pylint: disable=maybe-no-member
from collections import defaultdict
import importlib.abc
import importlib.util
import inspect
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple, cast
from marshmallow.schema import Schema
import logging
import inspect
import traceback

# pylint: disable=no-name-in-module
import wx
from rkviewer.plugin.classes import CommandPlugin, Plugin, PluginCategory, PluginType, WindowedPlugin
# pylint: disable=no-name-in-module
from wx.html import HtmlWindow

from rkviewer.config import add_plugin_schema
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
    callbacks: Dict[Plugin, Callable[[], None]]

    def __init__(self, parent_window: wx.Window, controller: IController):
        self.plugins = list()
        self.callbacks = dict()
        self.parent_window = parent_window
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
        self.logger = logging.getLogger('plugin-manager')
        self.error_callback = lambda _: None  # By default don't do anything

    def bind_error_callback(self, callback):
        """Bind a dialog callback for when there is an error.
        
        If an error occurs before such a callback is bound, it is only logged.
        """
        self.error_callback = callback

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
            mod_name = '_rkviewer.plugin_{}'.format(f[:-2])  # remove extension
            spec = importlib.util.spec_from_file_location(mod_name, os.path.join(dir_path, f))
            assert spec is not None
            mod = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            loader = cast(importlib.abc.Loader, spec.loader)
            try:
                loader.exec_module(mod)
            except Exception as e:
                except_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
                errmsg = "Failed to load plugin '{}':\n{}".format(f, except_str)
                self.logger.error(errmsg)
                self.error_callback(errmsg)
                continue

            def pred(o): return o.__module__ == mod_name and issubclass(o, Plugin)
            def wrap_exception(pname, method):
                def ret(*args, **kwargs):
                    try:
                        return method(*args, **kwargs)
                    except Exception as e:
                        errmsg = ''.join(traceback.format_exception(None, e, e.__traceback__))
                        errmsg = "Caught error in plugin '{}':\n".format(pname) + errmsg
                        self.logger.error(errmsg)
                        self.error_callback(errmsg)
                return ret

            cur_classes = [m[1] for m in inspect.getmembers(mod, inspect.isclass) if pred(m[1])]
            for cls in cur_classes:
                if inspect.isabstract(cls):
                    logging.warning("Plugin in file '{}' is an abstract class. Did not load.".format(f))
                    continue

                if not hasattr(cls, 'metadata'):
                    logging.warning("Plugin in file '{}' does not have a `metadata` class attribute. "
                        "Did not load. See plugin documentation for more information.".format(f))
                    continue
                
                for method_name, method in inspect.getmembers(cls, inspect.isroutine):
                    setattr(cls, method_name, wrap_exception(cls.metadata.name, method))

                plugin_classes.append(cls)

        logging.getLogger('plugin').info("Found {} valid plugins in '{}'. Loading plugins...".format(
            len(plugin_classes), dir_path))
        
        self.plugins = list()
        for cls in plugin_classes:
            try:
                plugin = cls()
                if not hasattr(plugin, 'ptype'):
                    logging.warning("Plugin '{}' has no `ptype` attribute. Did not load. "
                        "Did you forget to call `super().__init__()`?".format(cls.metadata.name))
                    continue
                self.plugins.append(cls())
            except Exception as e:
                self.logger.error('Error when creating plugin object: {}'.format(e))

        # Duplicate names
        if len(set(p.metadata.name for p in self.plugins)) < len(self.plugins):
            pass  # TODO fail when there is duplicate name.

        # Create and register callbacks
        for plugin in self.plugins:
            callback: Callable[[], None]
            if plugin.ptype == PluginType.COMMAND:
                plugin = cast(CommandPlugin, plugin)
                callback = self.make_command_callback(plugin)
            else:
                plugin = cast(WindowedPlugin, plugin)
                callback = self.make_windowed_callback(plugin, self.parent_window)
            self.callbacks[plugin] = callback

        # load schema
        for plugin in self.plugins:
            schema = plugin.get_settings_schema()
            if isinstance(schema, Schema):
                add_plugin_schema(plugin.metadata.name, schema)
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

    def register_menu(self, menu: wx.Menu):
        def _get_callback(plugin):
            return lambda _: self.callbacks[plugin]()

        sorted_plugins = sorted(self.plugins, key=lambda p: p.metadata.name)
        for plugin in sorted_plugins:
            item = menu.Append(wx.ID_ANY, plugin.metadata.name)
            menu.Bind(wx.EVT_MENU, _get_callback(plugin), item)

    def make_command_callback(self, command: CommandPlugin) -> Callable[[], None]:
        def command_cb():
            with self.controller.group_action():
                command.run()

        return command_cb

    def make_windowed_callback(self, windowed: WindowedPlugin,
                               parent: wx.Window) -> Callable[[], None]:
        title = windowed.metadata.name
        dialog_exists = False
        dialog: Optional[wx.Window] = None

        def windowed_cb():
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

    def get_plugins_by_category(self) -> Dict[PluginCategory, List[Tuple[str, Callable[[], None], Optional[wx.Bitmap]]]]:
        """Returns a dictionary that maps each category to the list of plugins.

        Each plugin in the lists is a tuple (short_name, bitmap, callback). The 
        """
        ret = defaultdict(list)
        for plugin in self.plugins:
            sname = plugin.metadata.short_name if plugin.metadata.short_name else plugin.metadata.name
            assert isinstance(plugin.metadata.category, PluginCategory)
            ret[plugin.metadata.category].append(
                (sname, self.callbacks[plugin], plugin.metadata.icon))
        return ret


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
