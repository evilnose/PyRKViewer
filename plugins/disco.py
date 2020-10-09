"""
The fill and border color of all nodes are set to a random color.

Version 0.01: Author: Gary Geng (2020)

"""

# pylint: disable=maybe-no-member
import wx
import random
from rkplugin.plugins import CommandPlugin, PluginMetadata
from rkplugin import api


metadata = PluginMetadata(
    name='Disco',
    author='Gary Geng',
    version='0.0.1',
    short_desc='Set all nodes to a random color.',
    long_desc='The fill and border color of all nodes are set to a random color.'
)


class Disco(CommandPlugin):
    def __init__(self):
        """
        Initialize the ColorSelected with no values for a Command Plugin.

        Args:
            self

        """
        super().__init__(metadata)

    def run(self):
        """
        Set the nodes to a random color.

        Args:
            self

        """
        nodes = api.get_nodes(api.cur_net_index())
        rgb = random.getrandbits(24)
        color = wx.Colour(rgb)
        for node in nodes:
            api.update_node(api.cur_net_index(), node.index, fill_color=color, border_color=color)
