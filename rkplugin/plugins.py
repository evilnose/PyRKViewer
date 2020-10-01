"""
The rkplugins.

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
    Defines the metadata information for a plugin.
    These include: name (str), author (str), version (str), short_desc (str), and long_desc (str)

    """
    name: str
    author: str
    version: str
    short_desc: str
    long_desc: str


class PluginType(Enum):
    """
    Defines the pluging type creating an ennumeration.

    """
    
    NULL = 0
    COMMAND = 1
    WINDOWED = 2


class Plugin:
    """
    Defines Plugin objects.

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

        TODO: document the following functions when written
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
    """
    Defines the command plugins.

    """
    def __init__(self, metadata: PluginMetadata):
        """
        Creating a CommandPlugin object.

        Args:
            self (self): CommandPlugin you are creating.
            metadata (PluginMetadata): metadata information of plugin.

        TODO: document the following functions when written
        """

        super().__init__(metadata, PluginType.COMMAND)

    # TODO: document the following functions when written
    @abc.abstractmethod
    def run(self):
        pass


class WindowedPlugin(Plugin, abc.ABC):
    def __init__(self, metadata: PluginMetadata):
        """
        Creating a WindowedPlugin object.

        Args:
            self (self): WindowedPlugin you are creating.
            metadata (PluginMetadata): metadata information of plugin.

        TODO: document the following functions when written
        """
        super().__init__(metadata, PluginType.WINDOWED)

    # TODO: document the following functions when written
    @abc.abstractmethod
    def create_window(self, dialog: wx.Window) -> wx.Window:
        pass

    def on_will_close_window(self, evt):
        evt.Skip()

    def on_did_focus(self):
        pass

    def on_did_unfocus(self):
        pass

