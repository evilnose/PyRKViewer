"""
The plugin base classes that the user should subclass from when creating plugins.
"""

# pylint: disable=maybe-no-member
from inspect import isabstract
from rkviewer.canvas.geometry import Vec2
from rkviewer.canvas.data import Node
from typing import List
import wx
import abc
from dataclasses import dataclass
from enum import Enum


@dataclass
class PluginMetadata:
    """
    Metadata for the plugin.

    Attributes:
        name: The display name of the plugin.
        author: The author of the plugin.
        version: The version string of the plugin.
        short_desc: A short description of the plugin. This is displayed as a tooltip, introduction,
                    etc.
        long_desc: A long, detailed description of the plugin. This is shown in the plugin details
                   page, as a comprehensive description of what this plugin does. This string will
                   be rendered as HTML.
    """
    name: str
    author: str
    version: str
    short_desc: str
    long_desc: str


class PluginType(Enum):
    """
    Enumeration of plugin types, dictating how a plugin would appear in the application.
    
    NULL: Null enumeration. There should not be a plugin instance with this type.
    COMMAND: A command plugin. See CommandPlugin for more details.
    WINDOWED: A windowed plugin. See WindowedPlugin for more details.
    """
    NULL = 0
    COMMAND = 1
    WINDOWED = 2


class Plugin:
    """
    The base class for a Plugin. 

    The user should not directly instantiate this but rather one of its subclasses,
    e.g. CommandPlugin.
    """
    metadata: PluginMetadata
    ptype: PluginType

    def __init__(self, metadata: PluginMetadata, ptype: PluginType):
        """
        Creating a Plugin object.

        Args:
            self (self): Plugin you are creating.
            metadata (PluginMetadata): metadata information of plugin.
            ptype (PluginType): defines the type of plugin to create.
        """
        self.metadata = metadata
        self.ptype = ptype

    # TODO: document the following functions when written
    def on_did_add_node(self, node: Node):
        pass

    def on_did_move_nodes(self, nodes: List[Node], offset: Vec2, dragged: bool):
        pass

    def on_did_commit_node_positions(self):
        pass

    def on_did_paint_canvas(self, gc: wx.GraphicsContext):
        pass

    def on_selection_did_change(self, node_indices: List[int], reaction_indices: List[int],
                                compartment_indices: List[int]):
        pass


class CommandPlugin(Plugin, abc.ABC):
    """Base class for simple plugins that is essentially one single command.

    One may think of a CommandPlugin as (obviously) a command, or a sort of macro in the simpler
    cases. The user may invoke the command defined when they click on the associated menu item
    under the "Plugins" menu, or they may be able to use a keybaord shortcut, once that is
    implemented. To subclass CommandPlugin one needs to override `run()`.
    """

    def __init__(self, metadata: PluginMetadata):
        """
        Create a CommandPlugin.

        Args:
            metadata (PluginMetadata): metadata information of plugin.
        """

        super().__init__(metadata, PluginType.COMMAND)

    @abc.abstractmethod
    def run(self):
        """Called when the user invokes this command manually.

        This should implement whatever action/macro that this Plugin claims to execute.
        """
        pass


class WindowedPlugin(Plugin, abc.ABC):
    def __init__(self, metadata: PluginMetadata):
        """Base class for plugins with an associated popup window.

        When the user clicks the menu item of this plugin under the "Plugins" menu, a popup dialog
        is created, which may display data, and which the user may interact with. This type of
        plugin is suitable to more complex or visually-based plugins, such as that utilizing a 
        chart or an interactive form.

        To implement a subclass of WindowedPlugin, one needs to override the method `create_window`.

        Args:
            metadata (PluginMetadata): metadata information of plugin.
        """
        super().__init__(metadata, PluginType.WINDOWED)

    @abc.abstractmethod
    def create_window(self, dialog: wx.Window) -> wx.Window:
        """Called when the user requests a dialog window from the plugin.

        For one overriding this method, they should either create or reuse a `wx.Window` instance
        to display in a dialog. One likely wants to bind events to the controls inside the returned
        `wx.Window` to capture user input.
        """
        pass

    def on_will_close_window(self, evt):
        """TODO not implemented"""
        evt.Skip()

    def on_did_focus(self):
        """TODO not implemented"""
        pass

    def on_did_unfocus(self):
        """TODO not implemented"""
        pass
