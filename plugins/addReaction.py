

"""
Add different reactions.
Version 0.01: Author: Jin Xu (2020)
"""


import wx
import wx.grid as  gridlib
from rkplugin.plugins import PluginMetadata, WindowedPlugin
from rkplugin import api
from rkplugin.api import Node, Vec2, Reaction, Color
import math
import random as _random
import numpy as _np
import copy as _copy
from dataclasses import dataclass


metadata = PluginMetadata(
    name='AddReaction',
    author='Jin Xu',
    version='0.01',
    short_desc='Add Reactions.',
    long_desc='Add different reactions.'
)



class AddReaction(WindowedPlugin):
    def __init__(self):
        """
        Initialize the StructuralAnalysis Plugin.
        Args:
            self
        """
        
        super().__init__(metadata)
        self.count_rct = 0      

    def create_window(self, dialog):
        """
        Create a window to do the structural analysis.
        Args:
            self
            dialog
        """
        window = wx.Panel(dialog, pos=(5,100), size=(300, 320))
 
        wx.StaticText(window, -1, 'Create different types of reactions', (50,10))

        UniUni_btn = wx.Button(window, -1, 'UniUni', (100, 50))
        UniUni_btn.Bind(wx.EVT_BUTTON, self.UniUni)

        BiUni_btn = wx.Button(window, -1, 'BiUni', (100, 110))
        BiUni_btn.Bind(wx.EVT_BUTTON, self.BiUni)

        UniBi_btn = wx.Button(window, -1, 'UniBi', (100, 170))
        UniBi_btn.Bind(wx.EVT_BUTTON, self.UniBi)

        BiBi_btn = wx.Button(window, -1, 'BiBi', (100, 230))
        BiBi_btn.Bind(wx.EVT_BUTTON, self.BiBi)

        window.SetPosition (wx.Point(10,10))
        return window

    def on_did_create_dialog(self):
        # Set position of popup window to top-left corner of screen
        self.dialog.SetPosition((240, 250))



    def UniUni(self, evt):

        """
        Handler for the "UniUni" button. add a UniUni reaction.
        """
        node_idx = []
        src = []
        dest = []

        # start group action context for undo purposes
        with api.group_action():
            try: 
                for index in api.selected_node_indices():
                    node_idx.append(index)

                src = _random.sample(node_idx, 1)
                for i in range(len(src)):
                    node_idx.remove(src[i])
                dest = _random.sample(node_idx, 1)
                    #node = api.get_node_by_index(0, index) #netindex = 0
                    #print(node.index)
                    #api.update_node(api.cur_net_index(), index, fill_color=color, border_color=color)
                r_idx = api.add_reaction(0, 'reaction_{}'.format(self.count_rct), src, dest, fill_color=api.Color(129, 123, 255))
                self.count_rct += 1
            except:
                wx.MessageBox("Error: try to select more than two nodes.", "Message", wx.OK | wx.ICON_INFORMATION)


    def BiUni(self, evt):

        """
        Handler for the "BiUni" button. add a BiUni reaction.
        """
        node_idx = []
        src = []
        dest = []

        # start group action context for undo purposes
        with api.group_action():
            try: 
                for index in api.selected_node_indices():
                    node_idx.append(index)
                src = _random.sample(node_idx, 2)
                for i in range(len(src)):
                    node_idx.remove(src[i])
                dest = _random.sample(node_idx, 1)
                r_idx = api.add_reaction(0, 'reaction_{}'.format(self.count_rct), src, dest, fill_color=api.Color(129, 123, 255))
                self.count_rct += 1
            except:
                wx.MessageBox("Error: try to select more than three nodes.", "Message", wx.OK | wx.ICON_INFORMATION)

    def UniBi(self, evt):

        """
        Handler for the "UniBi" button. add a UniBi reaction.
        """
        node_idx = []
        src = []
        dest = []

        # start group action context for undo purposes
        with api.group_action():
            try: 
                for index in api.selected_node_indices():
                    node_idx.append(index)

                src = _random.sample(node_idx, 1)
                for i in range(len(src)):
                    node_idx.remove(src[i])
                dest = _random.sample(node_idx, 2)
                r_idx = api.add_reaction(0, 'reaction_{}'.format(self.count_rct), src, dest, fill_color=api.Color(129, 123, 255))
                self.count_rct += 1
            except:
                wx.MessageBox("Error: try to select more than three nodes.", "Message", wx.OK | wx.ICON_INFORMATION)

    def BiBi(self, evt):

        """
        Handler for the "UniBi" button. add a UniBi reaction.
        """
        node_idx = []
        src = []
        dest = []

        # start group action context for undo purposes
        with api.group_action():
            try: 
                for index in api.selected_node_indices():
                    node_idx.append(index)

                src = _random.sample(node_idx, 2)
                for i in range(len(src)):
                    node_idx.remove(src[i])
                dest = _random.sample(node_idx, 2)
                r_idx = api.add_reaction(0, 'reaction_{}'.format(self.count_rct), src, dest, fill_color=api.Color(129, 123, 255))
                self.count_rct += 1
            except:
                wx.MessageBox("Error: try to select more than three nodes.", "Message", wx.OK | wx.ICON_INFORMATION)
    

  
