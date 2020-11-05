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

metadata = PluginMetadata(
    name='AutoLayoutTemp',
    author='Jin Xu, Herbert M Sauro',
    version='0.0.1',
    short_desc='Auto Layout.',
    long_desc='Rearrange a random network into a neat auto layout'
)

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
        self.MaxIterText = wx.TextCtrl(window, -1, "20", (280, 20), size=(100, -1))
        self.MaxIterText.SetInsertionPoint(0)
        self.MaxIterText.Bind(wx.EVT_TEXT, self.OnText_MaxIter)
        self.MaxIterValue = int(self.MaxIterText.GetValue())

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

        apply_btn = wx.Button(window, -1, 'Apply', (180, 240))
        apply_btn.Bind(wx.EVT_BUTTON, self.Apply)

        window.SetPosition (wx.Point(10,10))
        return window
    
    def OnText_MaxIter(self, evt):
        update = evt.GetString()
        if update != '':
            self.MaxIterValue = int(self.MaxIterText.GetValue())

    def OnText_k(self, evt):
        update = evt.GetString()
        if update != '':
            self.kValue = float(self.kText.GetValue())

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
        e = math.e
        # k = self.kValue # sqrt area / number of nodes
        gravity = self.gravityValue
        useMagnetism = self.useMagnetismValue
        useBoundary = self.useBoundaryValue
        useGrid = self.useGridValue

        def aF(d, k) -> float:
            return d*d/k
        
        def rF(d, k ) -> float:
            return k*k/d

        # Map a reaction index to the list of all pf its components
        def curves(reactions: List[Reaction]) -> dict():
            cur = {}
            for q in reactions:
                l = []
                for t in q.sources:
                    l.append(t)
                for w in q.targets:
                    l.append(w)
                cur[q.index] = l
            return cur

        def check_bounds(newX, newY, width, length, k) -> Vec2:
            if newX >= width:
                newX = width - (random.randrange(0, math.trunc(length/4)))
            if newY >= length:
                newY = length - (random.randrange(0, math.floor(length/4)))
            if newX <= 0:
                newX = random.randrange(0, math.floor(width/4))
                #newX = 0 + (k + uniform(0, width/4))
            if newY <= 0:
                newY = 0 + (random.randrange(0, math.floor(width/4)))

            return Vec2(newX, newY)

        def add(p1 : Vec2, p2: Vec2) -> Vec2:
            x = p1.x + p2.x
            y = p1.y + p2.y
            return Vec2(x, y)

        def minus(p1 : Vec2, p2: Vec2) -> Vec2:
            x = p1.x - p2.x
            y = p1.y - p2.y
            return Vec2(x, y)

        def distance(delta: Vec2) -> int:
            return math.sqrt(delta.x * delta.x + delta.y * delta.y)

        def fruchtermanReingold():
            canvas = api.canvas_size()
            

            numReactions = api.reaction_count(0)
            allNodes = api.get_nodes(0)
            numNodes = len(allNodes)
            allReactions = api.get_reactions(0)
            curs = curves(allReactions)

            
            width = canvas.x
            length = canvas.y
            area = width*length
            k = 120
            print(k)
            maxIter = math.trunc(100* math.log(numNodes + 2))
            tempinit = (1000 * math.log(numReactions + 2))
            tempcurr = tempinit
            time = 0.0 
            tIncrement = 1.0 / float(maxIter)
            alpha = math.log(tempinit) - math.log(0.25)
            adjustk = 0
            d: int
            delta = Vec2(0,0)
            barycenter = Vec2(width/2, length/2)

            
            
            # at node index keep its displacement
            Disp = dict()

            with api.group_action():
                for its in range(0, maxIter):
                    tempcurr = tempinit * math.pow(e, -alpha * time)
                    time = time + tIncrement

                    for f in allNodes:
                        Disp[f.index] = Vec2(0,0)

                    # Repulsive forces
                    for i in range(0, numNodes):
                        v = allNodes[i] 
                        vIndex = v.index
                        
                        for j in range(0, numNodes):
                            u = allNodes[j] 
                            uIndex = u.index
                            print(uIndex)
                            if (i != j):
                                delta = Vec2(v.position.x - u.position.x, v.position.y - u.position.y)
                                d = distance(delta)
                                if d == 0:
                                    d = 0.001
                                else:
                                    #vDeg = api.get_node_degree(0, vIndex)
                                    #uDeg = api.get_node_degree(0, uIndex)
                                    #adjustk = (k * math.log(vDeg + uDeg + 2))
                                    newDisp = Vec2(float(delta.x/d * rF(k, d)), float(delta.y/d * rF(k, d)))
                                    Disp[vIndex] = add(Disp[vIndex], newDisp)
                                    Disp[uIndex] = minus(Disp[uIndex], newDisp)
                    
                    # Attractive forces
                    # Each connection is reactant or product with centroid?
                    for r in curs:
                        cc = curs[r]
                        react = allReactions[r]
                        center = api.compute_centroid(0, react.sources, react.targets)
                        for c in cc:
                            v = api.get_node_by_index(0, c)
                            vIndex = v.index
                            vDeg = api.get_node_degree(0, vIndex)
                            delta = Vec2(v.position.x - center.x, v.position.y - center.y)
                            d = distance(delta)
                            if d != 0:
                                adjustk = (k * math.log(vDeg + len(cc) + 2))
                                newDisp= Vec2(delta.x/d * aF(adjustk, d), delta.y/d * aF(adjustk, d))
                                Disp[vIndex] = minus(Disp[vIndex], newDisp)
                                #newCent = Vec2(delta.x/d * aF(k, d), delta.y/d * aF(k, d))
                                #CentDisp[r] = add(CentDisp[r], newCent)
                    
                    # Magnetism
                    '''
                    if (useMagnetism):
                        for r in curs:
                            cc = curs[r]
                            react = allReactions[r]
                            for c1 in cc:
                                v = api.get_node_by_index(0, c)
                                vIndex = v.index
                                vType = api.node_type(0, vIndex, r)
                                vDegree = api.get_node_degree(0, vIndex)
                                for c2 in cc:
                                    u = api.get_node_by_index(0, c2)
                                    uIndex = u.index
                                    uType = api.node_type(0, uIndex, r)
                                    if (v != u and vType == uType and vType >= 0):
                                        delta = Vec2(v.position.x - u.position.x, v.position.y - u.position.y)
                                        d = distance(delta)
                                        if d != 0:
                                            vIndex = v.index
                                            uIndex = u.index
                                            vDeg = api.get_node_degree(0, vIndex)
                                            uDeg = api.get_node_degree(0, uIndex)
                                            adjustk = (k * math.log(vDeg + uDeg + 2))
                                            newDisp= Vec2(delta.x/d * rF(adjustk, d), delta.y/d * rF(adjustk, d))
                                            Disp[vIndex] = minus(Disp[vIndex], newDisp)
                                            Disp[uIndex] = add(Disp[uIndex], newDisp) 

                    '''
                    '''
                    # Gravity NOT READY
                    if (gravity > 5):
                        for i in allNodes:
                            v = i
                            delta = Vec2(v.position.x - barycenter.x, v.position.y - barycenter.y)
                            d = distance(delta)
                            adjustk = float(gravity)/ k
                            newDisp= Vec2(delta.x/d * d * adjustk, delta.y/d * d * adjustk)
                            Disp[vIndex] = minus(Disp[vIndex], newDisp)

                    '''
                    
                    # Adjust coordinates
                    for a in allNodes:
                        aInd = a.index
                        d = distance(Disp[aInd])
                        dx = Disp[aInd].x
                        dy = Disp[aInd].y
                        if (d != 0):
                            newX = a.position.x  + dx
                            newY = a.position.y  + dy
                            if (useBoundary):
                                check_bounds(newX, newY, width, length, k)
                            if (useGrid and tempcurr < k):
                                newX = float(math.floor(newX/k) * k)
                                newY = float(math.floor(newY/k) * k)

                            finalPos = Vec2(newX, newY)
                            '''for g in allNodes:
                                if ((a != g) and finalPos == g.position):
                                    shift = Vec2(math.trunc (random()*700), math.trunc (random()*600))
                                    finalPos = add(finalPos, shift)
                            newX = finalPos.x
                            newY = finalPos.y
                            '''
                            if (useBoundary):
                                finalPos = check_bounds(newX, newY, width, length, k)
                        
                        api.move_node(0, aInd, finalPos)
                                
                for r in api.get_reactions(0):
                    handles = api.default_handle_positions(0, r.index) # centroid, sources, target
                    sources = r.sources
                    targets = r.targets
                    api.set_reaction_center_handle(0, r.index, handles[0])
                    count = 1
                    for s in sources:
                        api.set_reaction_node_handle(0, r.index, s, True, handles[count])
                        count += 1
                    for t in targets:
                        api.set_reaction_node_handle(0, r.index, t, False, handles[count])
                        count += 1

        fruchtermanReingold()


                        
                                    
                        
