'''
Given a random network, this plugin  will rearrange the network neatly on the screen.
Version 0.01: Author: Carmen Perena Cortes 2020
Based on THOMAS M. J. FRUCHTERMAN AND EDWARD M. REINGOLD's Graph Drawing by Force-directed Placement
SOFTWARE—PRACTICE AND EXPERIENCE, VOL. 21(1 1), 1129-1164 (NOVEMBER 1991)
'''
import wx
from rkplugin.plugins import PluginMetadata, WindowedPlugin
from rkplugin import api
from rkplugin.api import Node, Vec2, Reaction
import math
from dataclasses import field
from typing import List
from random import uniform
from numpy.random import rand
import numpy as np
import random
from dataclasses import dataclass

metadata = PluginMetadata(
    name='NewAutolayout_New',
    author='Carmen and Herbert M Sauro',
    version='0.0.1',
    short_desc='Auto Layout.',
    long_desc='Rearrange a random network into a neat auto layout'
)
@dataclass
class TNode:
    x : float = 0.0
    y : float = 0.0
    dx : float = 0.0
    dy : float = 0.0

class AutoLayoutTemp(WindowedPlugin):
    def __init__(self):
        '''
        Initialize the RandomNetwork.
        Args:
            self
        '''
        super().__init__(metadata)
    def create_window(self, dialog):
        '''
        Create a window with several inputs and buttons.
        Args:
            self
            dialog
        '''
        # TODO: k, gravity, useMagnetism, useBoundary, useGrid
        window = wx.Panel(dialog, pos=(5,100), size=(400, 320))
        
        MaxIter = wx.StaticText(window, -1, 'Maximum Number of Iterations', (20 , 20))
        self.MaxIterText = wx.TextCtrl(window, -1, "200", (280, 20), size=(100, -1))
        self.MaxIterText.SetInsertionPoint(0)
        self.MaxIterText.Bind(wx.EVT_TEXT, self.OnText_MaxIter)
        self.MaxIterValue = int(self.MaxIterText.GetValue())

        k = wx.StaticText(window, -1, 'k (float > 0)', (20 , 50))
        self.kText = wx.TextCtrl(window, -1, "90", (280, 50), size=(100, -1))
        self.kText.SetInsertionPoint(0)
        self.kText.Bind(wx.EVT_TEXT, self.OnText_k)
        self.kValue = float(self.kText.GetValue())        



        gravity = wx.StaticText(window, -1, 'gravity (integer > 0)', (20 , 90))
        self.gravityText = wx.TextCtrl(window, -1, "10", (280, 90), size=(100, -1))
        self.gravityText.SetInsertionPoint(0)
        self.gravityText.Bind(wx.EVT_TEXT, self.OnText_gravity)
        self.gravityValue = int(self.gravityText.GetValue())

        useMagnetism = wx.StaticText(window, -1, 'Use Magnetism (True or False)', (20 , 120))
        self.useMagnetismText = wx.TextCtrl(window, -1, "True", (280, 120), size=(100, -1))
        self.useMagnetismText.SetInsertionPoint(0)
        self.useMagnetismText.Bind(wx.EVT_TEXT, self.OnText_useMagnetism)
        self.useMagnetismValue = bool(self.useMagnetismText.GetValue())

        useBoundary = wx.StaticText(window, -1, 'Use Boundary (set to False)', (20 , 150))
        self.useBoundaryText = wx.TextCtrl(window, -1, "True", (280, 150), size=(100, -1))
        self.useBoundaryText.SetInsertionPoint(0)
        self.useBoundaryText.Bind(wx.EVT_TEXT, self.OnText_useBoundary)
        self.useBoundaryValue = bool(self.useBoundaryText.GetValue())

        useGrid = wx.StaticText(window, -1, 'Use Grid (set to False)', (20 , 180))
        self.useGridText = wx.TextCtrl(window, -1, "False", (280, 180), size=(100, -1))
        self.useGridText.SetInsertionPoint(0)
        self.useGridText.Bind(wx.EVT_TEXT, self.OnText_useGrid)
        self.useGridValue = bool(self.useGridText.GetValue())
        
        apply_btn = wx.Button(window, -1, 'Apply', (280, 240))
        apply_btn.Bind(wx.EVT_BUTTON, self.Apply)
        
        self.iteration_label = wx.StaticText(window, -1, 'Iterations: ', (20 , 240))
 
        window.SetPosition (wx.Point(10,10))
        return window

    def OnText_MaxIter(self, evt):
        try:
          update = evt.GetString()
          if update != '':
              self.MaxIterValue = int(self.MaxIterText.GetValue())
        except ValueError:
           wx.MessageBox('Value must be a number', 'Error', wx.OK | wx.ICON_INFORMATION)

    def OnText_k(self, evt):
        try:
           update = evt.GetString()
           if update != '':
              self.kValue = float(self.kText.GetValue())
        except ValueError:
           wx.MessageBox('Value must be a number', 'Error', wx.OK | wx.ICON_INFORMATION)


    def OnText_gravity(self, evt):
        update = evt.GetString()
        if update != '':
            self.gravityValue = int(self.gravityText.GetValue())

    def OnText_useBoundary(self, evt):
        update = evt.GetString()
        if update != '':
            self.useBoundaryValue = bool(self.useBoundaryText.GetValue())
    
    def OnText_useGrid(self, evt):
        update = evt.GetString()
        if update != '':
            self.useGridValue = bool(self.useGridText.GetValue())
    
    def OnText_useMagnetism(self, evt):
        update = evt.GetString()
        if update != '':
            self.useMagnetismValue = bool(self.useMagnetismText.GetValue())
    
    def Apply(self, evt):
        '''
        Handler for the "apply" button. apply the random network.
        Adapting the Fruchterman Reingold algorithm to auto layout
        '''
        enumber = math.e
        # k = self.kValue # sqrt area / number of nodes
        gravity = self.gravityValue
        useMagnetism = self.useMagnetismValue
        useBoundary = self.useBoundaryValue
        useGrid = self.useGridValue

        def getCenter (node):
            x = node.position.x + node.size.x/2
            y = node.position.y + node.size.y/2
            return Vec2 (x, y)

        def fruchtermanReingold():
            canvas = api.canvas_size()
            finished = False
            numReactions = api.reaction_count(0)
            allNodes = api.get_nodes(0)
            numNodes = len(allNodes)
            allReactions = api.get_reactions(0)

            if numNodes == 0:
              wx.MessageBox('Please load a model first', 'Info', wx.OK | wx.ICON_INFORMATION)
              return  

            if numReactions == 0:
              wx.MessageBox('There should be a least one reaction', 'Info', wx.OK | wx.ICON_INFORMATION)
              return  

            # Store the dx, dy values for a given node
            displacement = dict()
            for v in api.get_nodes(0):
                displacement[v.index] = TNode()

            area = canvas.x*canvas.y

            k = math.sqrt(area/numNodes)/10
            k = self.kValue

            maxIter = math.trunc(130 * math.log(numNodes + 2)) + 1000
            tempinit = (100 * math.log(numReactions + 2))
            alpha = math.log(tempinit) - math.log(0.25)
            dt = 1/(maxIter + 1)
            
            iteration = 0
            maxIter = 200

            t = tempinit * enumber**(-alpha * 0.5)
            
            listOfReactions = api.get_reactions(0)
            
            with api.group_action():
            #if True:  # Uncomment if you want to see it move
                while not finished:
                    # calculate repulsive forces
                    for v in api.get_nodes (0):
                        nodeIndexV = v.index
                        displacement[nodeIndexV].dx = 0.0
                        displacement[nodeIndexV].dy = 0.0
                        for u in api.get_nodes(0):
                            if v.index != u.index:
                               centerU = u.position
                               centerV = v.position
                               dx = centerV.x - centerU.x
                               dy = centerV.y - centerU.y
                               dist = math.sqrt(dx*dx + dy*dy)
                               if dist > 0:
                                  repulsiveF = k*k/dist
                                  displacement[nodeIndexV].dx = displacement[nodeIndexV].dx + (dx/dist)*repulsiveF
                                  displacement[nodeIndexV].dy = displacement[nodeIndexV].dy + (dy/dist)*repulsiveF
                    
                    # calculate attractive forces
                    for reaction in listOfReactions:
                        srcNodeIndex = reaction.sources[0]
                        destNodeIndex = reaction.targets[0]
                        srcNode = api.get_node_by_index (0, srcNodeIndex)
                        destNode = api.get_node_by_index (0, destNodeIndex)
                        dx = srcNode.position.x - destNode.position.x
                        dy = srcNode.position.y - destNode.position.y
                        dist = math.sqrt(dx*dx+dy*dy)
                        if dist > 0:
                           attractiveF = dist * dist / k
                           ddx = dx*attractiveF/dist
                           ddy = dy*attractiveF/dist
                           displacement[srcNodeIndex].dx = displacement[srcNodeIndex].dx - ddx
                           displacement[srcNodeIndex].dy = displacement[srcNodeIndex].dy - ddy
                           displacement[destNodeIndex].dx = displacement[destNodeIndex].dx + ddx
                           displacement[destNodeIndex].dy = displacement[destNodeIndex].dy + ddy
                    
                    # Adjust Coordinates
                    sum = 0.0
                    for v in api.get_nodes(0):
                          #if not network.nodes[v].locked then
                        dx = displacement[v.index].dx
                        dy = displacement[v.index].dy
                        sum = sum + abs (dx) + abs (dy)
                        dist = math.sqrt(dx*dx+dy*dy);
                        if (dist > 0):
                           if t < abs (dx):
                              f1 = t
                           else:
                              f1 = dx
                           if t < abs (dy):
                              f2 = t
                           else:
                              f2 = dy
                           pos = Vec2 (v.position.x + dx/dist*f1, v.position.y + dy/dist*f2)
                           api.move_node(0, v.index, pos)
                    
                    wx.Yield()
                    
                    t = t * 1#0.95 # Not sure if this makes any difference
                    iteration = iteration + 1
                    self.iteration_label.SetLabel ('Iterations: ' + str (iteration))
                    if iteration > maxIter:
                        print ("IterMax reached")
                        finished = True                 
           
            for r in api.get_reactions(0):
                handles = api.default_handle_positions(0, r.index) # centroid, sources, target
                api.set_reaction_center_handle(0, r.index, handles[0])
                count = 1
                for s in r.sources:
                    api.set_reaction_node_handle(0, r.index, s, True, handles[count])
                    count += 1
                for t in r.targets:
                    api.set_reaction_node_handle(0, r.index, t, False, handles[count])
                    count += 1
        
        fruchtermanReingold()