

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
        self.node_idx_list = []

    def create_window(self, dialog):
        """
        Create a window to do the structural analysis.
        Args:
            self
            dialog
        """
        window = wx.Panel(dialog, pos=(5,100), size=(300, 320))
 
        wx.StaticText(window, -1, '1.Refresh before clicking nodes to add each reaction.', (5,10))

        SelectNodes_btn = wx.Button(window, -1, 'Refresh', (50, 40))
        SelectNodes_btn.Bind(wx.EVT_BUTTON, self.restart_node_idx)

        wx.StaticText(window, -1, '2.Click nodes for each reaction.', (5,90))

        wx.StaticText(window, -1, '3.Create different types of reactions.', (5,130))

        UniUni_btn = wx.Button(window, -1, 'UniUni', (50, 170))
        UniUni_btn.Bind(wx.EVT_BUTTON, self.UniUni)

        BiUni_btn = wx.Button(window, -1, 'BiUni', (150, 170))
        BiUni_btn.Bind(wx.EVT_BUTTON, self.BiUni)

        UniBi_btn = wx.Button(window, -1, 'UniBi', (50, 230))
        UniBi_btn.Bind(wx.EVT_BUTTON, self.UniBi)

        BiBi_btn = wx.Button(window, -1, 'BiBi', (150, 230))
        BiBi_btn.Bind(wx.EVT_BUTTON, self.BiBi)

        window.SetPosition (wx.Point(10,10))
        return window

    def on_did_create_dialog(self):
        # Set position of popup window to top-left corner of screen
        self.dialog.SetPosition((240, 250))


    def on_selection_did_change(self, evt):
        """
        Overrides base class event handler to update number of items selected.
        Args:
            self
            node_indices(List[int]): List of node indices changed.
            reaction_indices (List[int]): List of reaction indices changed.
            compartment_indices (List[int]): List of compartment indices changed.
        """
        self.node_clicked = list(evt.node_indices)
        try:
            self.node_idx_list.append(self.node_clicked[0])
        except:
                wx.MessageBox("Error: No nodes are selected.", "Message", wx.OK | wx.ICON_INFORMATION)        

    def restart_node_idx(self, evt):
        try:
            self.node_idx_list = []
        except:
            wx.MessageBox("Error: Can not refresh.", "Message", wx.OK | wx.ICON_INFORMATION)

    def UniUni(self, evt):

        """
        Handler for the "UniUni" button. add a UniUni reaction.
        """
        src = []
        dest = []

        #print(self.node_clicked)
        #print(self.node_idx_list)

        # start group action context for undo purposes
        with api.group_action():
            try: 
                for i in range(1):
                    src.append(self.node_idx_list[i])
                for i in range(1,2):
                    dest.append(self.node_idx_list[i])
                
                #print(src)
                #print(dest)

                r_idx = api.add_reaction(0, 'reaction_{}'.format(self.count_rct), src, dest, fill_color=api.Color(129, 123, 255))
                self.count_rct += 1
            except:
                wx.MessageBox("Error: try to click more than two nodes.", "Message", wx.OK | wx.ICON_INFORMATION)


    def BiUni(self, evt):

        """
        Handler for the "BiUni" button. add a BiUni reaction.
        """
        src = []
        dest = []

        # start group action context for undo purposes
        with api.group_action():
            try: 
                for i in range(2):
                    src.append(self.node_idx_list[i])
                for i in range(2,3):
                    dest.append(self.node_idx_list[i])

                r_idx = api.add_reaction(0, 'reaction_{}'.format(self.count_rct), src, dest, fill_color=api.Color(129, 123, 255))
                self.count_rct += 1
            except:
                wx.MessageBox("Error: try to click more than three nodes.", "Message", wx.OK | wx.ICON_INFORMATION)

    def UniBi(self, evt):

        """
        Handler for the "UniBi" button. add a UniBi reaction.
        """
        src = []
        dest = []

        # start group action context for undo purposes
        with api.group_action():
            try: 
                for i in range(1):
                    src.append(self.node_idx_list[i])
                for i in range(1,3):
                    dest.append(self.node_idx_list[i])

                r_idx = api.add_reaction(0, 'reaction_{}'.format(self.count_rct), src, dest, fill_color=api.Color(129, 123, 255))
                self.count_rct += 1
            except:
                wx.MessageBox("Error: try to click more than three nodes.", "Message", wx.OK | wx.ICON_INFORMATION)

    def BiBi(self, evt):

        """
        Handler for the "UniBi" button. add a UniBi reaction.
        """
        src = []
        dest = []

        # start group action context for undo purposes
        with api.group_action():
            try: 
                for i in range(2):
                    src.append(self.node_idx_list[i])
                for i in range(2,4):
                    dest.append(self.node_idx_list[i])
                r_idx = api.add_reaction(0, 'reaction_{}'.format(self.count_rct), src, dest, fill_color=api.Color(129, 123, 255))
                self.count_rct += 1
            except:
                wx.MessageBox("Error: try to click more than four nodes.", "Message", wx.OK | wx.ICON_INFORMATION)
    

  
