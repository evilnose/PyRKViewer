

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
import copy


metadata = PluginMetadata(
    name='AddReaction_HMS_B',
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
        self.uniuniState = False
        self.biuniState = False
        self.unibiState = False
        self.bibiState = False
        self.src = []
        self.dest = []
        self.nodes = []

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

        self.UniUni_btn = wx.Button(window, -1, 'UniUni', (50, 170))
        self.UniUni_btn.Bind(wx.EVT_BUTTON, self.UniUni)

        self.BiUni_btn = wx.ToggleButton(window, -1, 'BiUni', (150, 170))
        self.BiUni_btn.Bind(wx.EVT_TOGGLEBUTTON, self.BiUni)

        self.UniBi_btn = wx.ToggleButton(window, -1, 'UniBi', (50, 230))
        self.UniBi_btn.Bind(wx.EVT_TOGGLEBUTTON, self.UniBi)

        self.BiBi_btn = wx.ToggleButton(window, -1, 'BiBi', (150, 230))
        self.BiBi_btn.Bind(wx.EVT_TOGGLEBUTTON, self.BiBi)

        window.SetPosition (wx.Point(10,10))
        return window

    def on_did_create_dialog(self):
        # Set position of popup window to top-left corner of screen
        self.dialog.SetPosition((240, 250))


    def getUniqueName(self, base: str, names: list) -> str:
        increment = 0
        # keep incrementing until you find a unique Id
        while True:
            suffix = '_{}'.format(increment)

            cur_id = base + suffix

            if cur_id in names:
                increment += 1
                continue
            else:
                # loop finished normally; done
                return cur_id

    def addReaction (self, src, dest):
        # Common to all reactions
        names = []
        # Get a unique reaction name
        for r in api.get_reactions (0):
            names.append (r.id_)           
        reactionId = self.getUniqueName('reaction', names)
        r_idx = api.add_reaction(0, reactionId, src, dest, fill_color=api.Color(129, 123, 255))

    def on_selection_did_change(self, evt):
        """
        Overrides base class event handler to update number of items selected.
        Args:
            self
            node_indices(List[int]): List of node indices changed.
            reaction_indices (List[int]): List of reaction indices changed.
            compartment_indices (List[int]): List of compartment indices changed.
        """

        if len (list(evt.node_indices)) == 0:
           self.src = []
           self.dest = []
           #self.uniuniState = False  
           #self.biuniState = False  
           #self.unibiState = False  
           #self.bibiState = False             
           return

        #if (not self.uniuniState) and (not self.biuniState) and \
        #      (not self.unibiState) and (not self.bibiState):
        #   return

        self.node_clicked = list(evt.node_indices)

        try:
          self.nodes = copy.deepcopy (list(evt.node_indices))

        except:
          pass
          #wx.MessageBox("Error: Try again", "Message", wx.OK | wx.ICON_INFORMATION)

    def restart_node_idx(self, evt):
        try:
            self.node_idx_list = []
        except:
            wx.MessageBox("Error: Can not refresh.", "Message", wx.OK | wx.ICON_INFORMATION)

    def UniUni(self, evt):

        """
        Handler for the "UniUni" button. add a UniUni reaction.
        """
        print ("UniUni")
        self.src.append (self.nodes[0])
        self.dest.append (self.nodes[1])         
        self.addReaction (self.src, self.dest)

    def BiUni(self, evt):

        """
        Handler for the "BiUni" button. add a BiUni reaction.
        """
        state = evt.GetEventObject().GetValue()
        if state == True:  
           self.src = []
           self.dest = []
           self.uniuniState = False
           self.biuniState = True
           self.unibiState = False
           self.bibiState = False  
           self.UniUni_btn.SetValue (False)          
           self.UniBi_btn.SetValue (False) 
           self.BiBi_btn.SetValue (False)  
        else:
           self.biuniState = False


    def UniBi(self, evt):

        """
        Handler for the "UniBi" button. add a UniBi reaction.
        """
        state = evt.GetEventObject().GetValue()
        if state == True:  
           self.src = []
           self.dest = []
           self.uniuniState = False
           self.biuniState = False
           self.unibiState = True
           self.bibiState = False  
           self.UniUni_btn.SetValue (False)          
           self.BiUni_btn.SetValue (False) 
           self.BiBi_btn.SetValue (False)                        
        else:
           self.biuniState = False

    def BiBi(self, evt):

        """
        Handler for the "UniBi" button. add a UniBi reaction.
        """
        state = evt.GetEventObject().GetValue()
        if state == True:  
           self.src = []
           self.dest = []
           self.uniuniState = False
           self.biuniState = False
           self.unibiState = False
           self.bibiState = True 
           self.UniUni_btn.SetValue (False)          
           self.BiUni_btn.SetValue (False) 
           self.UniBi_btn.SetValue (False)                        
        else:
           self.biuniState = False

  
