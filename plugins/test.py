"""
Display a random network.

Version 0.01: Author: Jin Xu, Herbert M Sauro (2020)

"""


import wx
from rkplugin.plugins import PluginMetadata, WindowedPlugin
from rkplugin import api
from rkplugin.api import Node, Vec2, Reaction
import math
import random as _random
import numpy as _np
import copy as _copy
from dataclasses import dataclass



metadata = PluginMetadata(
    name='Test',
    author='Jin Xu, Herbert M Sauro',
    version='0.0.1',
    short_desc='Random network.',
    long_desc='Display a random network.'
)

class RandomNetwork(WindowedPlugin):
    def __init__(self):
        """
        Initialize the RandomNetwork.

        Args:
            self

        """
        super().__init__(metadata)

    def create_window(self, dialog):
        """
        Create a window with several inputs and buttons.
        Args:
            self
            dialog
        """

        window = wx.Window(dialog, pos=(5,100), size=(300, 320))

        apply_btn = wx.Button(window, -1, 'Create Nodes', (60, 40))
        apply_btn.Bind(wx.EVT_BUTTON, self.Apply)

        move_btn = wx.Button(window, -1, 'Move', (60, 90))
        move_btn.Bind(wx.EVT_BUTTON, self.moveNode)

        window.SetPosition (wx.Point(10,10))
        return window

    def moveNode (self, evt):

        x = 40; y = 40; count = 1
        for index in self.nodeIdx:
            node = api.get_node_by_index (0, index)
            #pos = node.position + Vec2(x, y)
            api.update_node (0, index, position=Vec2(x, y))
            x = x + 100;
            if count % 3 == 0:
               y = y + 100
               x = 40
            count = count + 1
        

    def Apply(self, evt):    

        net_index = 0
        
        api.clear_network(net_index)

        self.nodeIdx = []
        for i in range (12):
            self.nodeIdx.append (api.add_node(net_index, 'node_' + str (i), size=Vec2(60,40), fill_color=api.Color(255, 179, 175),
                    border_color=api.Color(255, 105, 97),
                    position=Vec2(40 + math.trunc (_random.random()*500), 40 + math.trunc (_random.random()*500))))
       
 
        #r_idx = api.add_reaction(net_index, 'reaction_1', [self.b1], [self.b2], fill_color=api.Color(129, 123, 255))    
        #r_idx = api.add_reaction(net_index, 'reaction_2', [self.b2], [self.b3], fill_color=api.Color(129, 123, 255))
      

