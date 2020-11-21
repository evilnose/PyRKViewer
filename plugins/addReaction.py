"""
Add different reactions.
Version 0.01: Author: Jin Xu and Herbert Sauro (2020)
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
    author='Jin Xu and Herbert Sauro',
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

    def create_window(self, dialog):
        """
        Create a window to do the structural analysis.
        Args:
            self
            dialog
        """
        window = wx.Panel(dialog, pos=(5,100), size=(150, 190))
 
        wx.StaticText(window, -1, 'Select reaction type', (15,10))
        wx.StaticText(window, -1, 'then select nodes:', (15,25))

        self.UniUni_btn = wx.ToggleButton(window, -1, 'UniUni', (36, 22+25), size=(62,22))
        self.UniUni_btn.Bind(wx.EVT_TOGGLEBUTTON, self.UniUni)

        self.BiUni_btn = wx.ToggleButton(window, -1, 'BiUni', (36, 47+25), size=(62,22))
        self.BiUni_btn.Bind(wx.EVT_TOGGLEBUTTON, self.BiUni)

        self.UniBi_btn = wx.ToggleButton(window, -1, 'UniBi', (36, 72+25), size=(62,22))
        self.UniBi_btn.Bind(wx.EVT_TOGGLEBUTTON, self.UniBi)

        self.BiBi_btn = wx.ToggleButton(window, -1, 'BiBi', (36, 97+25), size=(62,22))
        self.BiBi_btn.Bind(wx.EVT_TOGGLEBUTTON, self.BiBi)

        window.SetPosition (wx.Point(10,10))
        return window

    def on_did_create_dialog(self):
        # Set position of popup window to top-left corner of screen
        self.dialog.SetPosition((240, 250))

    def on_will_close_window(self, evt):
        self.uniuniState = False
        self.biuniState = False
        self.unibiState = False
        self.bibiState = False
        evt.Skip()

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
           return

        if (not self.uniuniState) and (not self.biuniState) and \
              (not self.unibiState) and (not self.bibiState):
           return

        self.node_clicked = list(evt.node_indices)
       
        try:
            if self.uniuniState:
               if len(self.src) == 0:
                  self.src.append (self.node_clicked[0])
                  return

               if len (self.dest) == 0:
                  self.dest.append (self.node_clicked[0])
                  self.addReaction (self.src, self.dest)
                  return

            if self.biuniState:
               if len(self.src) == 0:
                  self.src.append (self.node_clicked[0])
                  return

               if len (self.src) == 1:
                  self.src.append (self.node_clicked[0])
                  return

               if (len (self.src) <= 2) and len (self.dest) == 0:
                  self.dest.append (self.node_clicked[0])
                  self.addReaction (self.src, self.dest)
                  return          

            if self.unibiState:
               if len(self.src) == 0:
                  self.src.append (self.node_clicked[0])
                  return

               if len (self.dest) == 0:
                  self.dest.append (self.node_clicked[0])
                  return
               
               if (len (self.src) <= 1) and len (self.dest) == 1:
                  self.dest.append (self.node_clicked[0])
                  self.addReaction (self.src, self.dest)
                  return

            if self.bibiState:
               if len(self.src) == 0:
                  self.src.append (self.node_clicked[0])
                  return

               if len (self.src) == 1:
                  self.src.append (self.node_clicked[0])
                  return

               if len (self.dest) == 0:
                  self.dest.append (self.node_clicked[0])
                  return

               if (len (self.src) <= 2) and len (self.dest) == 1:
                  self.dest.append (self.node_clicked[0])
                  self.addReaction (self.src, self.dest)
                  return
        except:
           pass #wx.MessageBox("Error: Try again", "Message", wx.OK | wx.ICON_INFORMATION)

    def UniUni(self, evt):
        """
        Handler for the "UniUni" button. add a UniUni reaction.
        """
        state = evt.GetEventObject().GetValue()
        if state == True:  
           self.src = []
           self.dest = []
           # This code is to make the buttons work as a radionbutton
           self.uniuniState = True
           self.biuniState = False
           self.unibiState = False
           self.bibiState = False
           self.BiUni_btn.SetValue (False)
           self.UniBi_btn.SetValue (False)
           self.BiBi_btn.SetValue (False)            
        else:
           self.uniuniState = False

    def BiUni(self, evt):
        """
        Handler for the "BiUni" button. add a BiUni reaction.
        """
        state = evt.GetEventObject().GetValue()
        if state == True:  
           self.src = []
           self.dest = []

           # This code is to make the buttons work as a radionbutton
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

           # This code is to make the buttons work as a radionbutton          
           self.uniuniState = False
           self.biuniState = False
           self.unibiState = True
           self.bibiState = False  
           self.UniUni_btn.SetValue (False)          
           self.BiUni_btn.SetValue (False)
           self.BiBi_btn.SetValue (False)                        
        else:
           self.unibiState = False

    def BiBi(self, evt):
        """
        Handler for the "UniBi" button. add a UniBi reaction.
        """
        state = evt.GetEventObject().GetValue()
        if state == True:  
           self.src = []
           self.dest = []

           # This code is to make the buttons work as a radionbutton
           self.uniuniState = False
           self.biuniState = False
           self.unibiState = False
           self.bibiState = True
           self.UniUni_btn.SetValue (False)          
           self.BiUni_btn.SetValue (False)
           self.UniBi_btn.SetValue (False)                        
        else:
           self.bibiState = False
