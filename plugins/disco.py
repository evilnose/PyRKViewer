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
        super().__init__(metadata)

    def run(self):
        nodes = api.all_nodes()
        rgb = random.getrandbits(24)
        color = wx.Colour(rgb)
        for node in nodes:
            api.set_node_fill(api.cur_net_index(), node.index, color)
            api.set_node_border(api.cur_net_index(), node.index, color)
