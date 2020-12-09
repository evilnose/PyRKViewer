"""
The fill and border color of all nodes are set to a random color.

Version 0.01: Author: Gary Geng (2020)

"""

# pylint: disable=maybe-no-member
from rkplugin.api import Color
import wx
import random
from rkplugin.plugins import CommandPlugin, PluginMetadata, PluginCategory
from rkplugin import api


metadata = PluginMetadata(
    name='Disco',
    author='Gary Geng',
    version='0.0.1',
    short_desc='Set all nodes to a random color.',
    long_desc='The fill and border color of all nodes are set to a random color.',
    category=PluginCategory.MISC,
)


class Disco(CommandPlugin):
    def __init__(self):
        """
        Initialize the CommandPlugin with the given metadata.
        """
        super().__init__(metadata)

    def run(self):
        """
        Set all nodes in the given network to a random color.
        """
        nodes = api.get_nodes(api.cur_net_index())
        rgb = random.getrandbits(24)
        color = Color.from_rgb(rgb)
        for node in nodes:
            api.update_node(api.cur_net_index(), node.index, fill_color=color, border_color=color)
