"""
The plugin base classes that the user should subclass from when creating plugins.
"""

# pylint: disable=maybe-no-member
from inspect import isabstract
from rkviewer.events import (DidAddCompartmentEvent, DidAddNodeEvent, DidAddReactionEvent, DidChangeCompartmentOfNodesEvent, DidCommitDragEvent, DidDeleteEvent, DidModifyCompartmentsEvent, DidModifyNodesEvent, DidModifyReactionEvent, DidMoveBezierHandleEvent, DidMoveCompartmentsEvent,
                             DidMoveNodesEvent, DidPaintCanvasEvent, DidRedoEvent, DidResizeCompartmentsEvent, DidResizeNodesEvent, SelectionDidUpdateEvent, DidUndoEvent)
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

    def on_did_add_node(self, evt: DidAddNodeEvent):
        """Called after a node is added."""
        pass

    def on_did_move_nodes(self, evt: DidMoveNodesEvent):
        """Called after nodes are moved."""
        pass

    def on_did_resize_nodes(self, evt: DidResizeNodesEvent):
        """Called after nodes are resized."""
        pass

    def on_did_add_compartment(self, evt: DidAddCompartmentEvent):
        """Called after a compartment is added."""
        pass

    def on_did_resize_compartments(self, evt: DidResizeCompartmentsEvent):
        """Called after compartments are resized."""
        pass

    def on_did_move_compartments(self, evt: DidMoveCompartmentsEvent):
        """Called after compartments are moved."""
        pass

    def on_did_add_reaction(self, evt: DidAddReactionEvent):
        """Called after a reaction is added."""
        pass

    def on_did_undo(self, evt: DidUndoEvent):
        """Called after an undo operation is performed."""
        pass

    def on_did_redo(self, evt: DidRedoEvent):
        """Called after an redo operation is performed."""
        pass

    def on_did_delete(self, evt: DidDeleteEvent):
        """Called after items (nodes, reactions, and/or compartments) are deleted."""
        pass

    def on_did_commit_drag(self, evt: DidCommitDragEvent):
        """Called after a dragging operation has been committed to the model."""
        pass

    def on_did_paint_canvas(self, evt: DidPaintCanvasEvent):
        """Called each time the canvas is painted."""
        pass

    def on_selection_did_change(self, evt: SelectionDidUpdateEvent):
        """Called after the set of selected items have changed."""
        pass

    def on_did_move_bezier_handle(self, evt: DidMoveBezierHandleEvent):
        """Called as the Bezier handles are being moved."""
        pass

    def on_did_modify_nodes(self, evt: DidModifyNodesEvent):
        """Called after properties of nodes (other than position/size) have been modified"""
        pass

    def on_did_modify_reactions(self, evt: DidModifyReactionEvent):
        """Called after properties of reactions have been modified."""
        pass

    def on_did_modify_compartments(self, evt: DidModifyCompartmentsEvent):
        """Called after properties of compartments (other than position/size) have been modified"""
        pass

    def on_did_change_compartment_of_nodes(self, evt: DidChangeCompartmentOfNodesEvent):
        """Called after the compartment that some nodes are in has changed."""
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
