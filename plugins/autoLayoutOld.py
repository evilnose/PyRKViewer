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

metadata = PluginMetadata(
    name='AutoLayout',
    author='Carmen Perena, Herbert M Sauro',
    version='0.0.1',
    short_desc='Auto Layout.',
    long_desc='Rearrange a random network into a neat auto layout'
)

class AutoLayout(WindowedPlugin):
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
        self.MaxIterText = wx.TextCtrl(window, -1, "215", (280, 20), size=(100, -1))
        self.MaxIterText.SetInsertionPoint(0)
        self.MaxIterText.Bind(wx.EVT_TEXT, self.OnText_MaxIter)
        self.MaxIterValue = int(self.MaxIterText.GetValue())

        k = wx.StaticText(window, -1, 'k (float > 0)', (20 , 50))
        self.kText = wx.TextCtrl(window, -1, "0.5", (280, 50), size=(100, -1))
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
        self.useBoundaryText = wx.TextCtrl(window, -1, "False", (280, 150), size=(100, -1))
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

        # TODO: look at these variables
        e = math.e

        # TODO: make these into inputs
        k = self.kValue
        gravity = self.gravityValue
        useMagnetism = self.useMagnetismValue
        useBoundary = self.useBoundaryValue
        useGrid = self.useGridValue

        def attractiveForce(d, k) -> float:
            return k*k/d
        
        def repulsiveForce(d, k ) -> float:
            return k*k/d

        class Connection:
            reactant: int = field()
            product: int = field()


        # Make a list of all pairs in each reaction
        def pairList(reactions: List[Reaction]) -> List[List[Connection]]:
            con = []
            for q in reactions:
                qList = []
                for t in q.sources:
                    for w in q.targets:
                        qList.append(Connection(t, w))
                con.insert(q, qList) 
            return con

        def curves(reactions: List[Reaction]) -> List[List[int]]:
            cur = []
            for q in reactions:
                l = []
                for t in q.sources:
                    l.append(t)
                for w in q.targets:
                    l.append(w)
                cur.append(l)
            return cur

        class PointF:
            def __init__(self, x, y):
                self.x = x
                self.y = y

            
            '''
            def add(self, p : PointF) -> PointF:
                self.x = self.x + p.x
                self.y = self.y + p.y
                return PointF(self.x, self.y)

            def minus(self, p : PointF) -> PointF:
                self.x = self.x - p.x
                self.y = self.y - p.y
                return PointF(self.x, self.y)
            '''
        
        def add(p1 : PointF, p2: PointF) -> PointF:
            x = p1.x + p2.x
            y = p1.y + p2.y
            return PointF(x, y)

        def minus(p1 : PointF, p2: PointF) -> PointF:
            x = p1.x - p2.x
            y = p1.y - p2.y
            return PointF(x, y)


        def fruchtermanReingold(self, canvasSize):
            # TODO: the node_count makes no sense
            # netIn = api.cur_net_index
            netIn = 0
            #numNodes = api.node_count(netIn)
            #print("numNodes: %d" % numNodes)
            numReactions = api.reaction_count(netIn)
            #print ("n: %d" % numReactions)
            allNodes = api.get_nodes(netIn)
            numNodes = len(allNodes)
            # TODO: throw exceptions
            allReactions = api.get_reactions(netIn)
            #print("all reactions:")
            #print(allReactions)
            # cons = pairList(allReactions)
            curs = curves(allReactions)
            #print ("curs: ")
            #print (curs)

            # TODO: decide if input of not
            maxIter = math.trunc(100* math.log(numNodes + 2))
            tempinit = (1000 * math.log(numReactions + 2))
            tempcurr = tempinit
            time = 0.0 
            tIncrement = 1.0
            alpha = math.log(tempinit) - math.log(0.25)
            adjustk = 0

            #area = windowSize[0] * windowSize[1]
            
            its: int
            d: int
            delta = PointF(0, 0)
            width = math.sqrt(numNodes)* k * 5 # TODO: WHY
            length = width
            area = width*length
            #k = math.sqrt(area/numNodes)
            baryCenter = PointF(0, 0)

            # displacement of nodes, index = node index
            Pos = []
            # displacement of centroids, index = reaction index
            CentDisp = []
            for y in range(0, numNodes + 1):
                Pos.append(PointF(0,0))

            for y in range(0, numReactions + 1):
                CentDisp.append(PointF(0,0))

            #each curve[i] is a reaction and the list corresponding are the curves
            Curves = []

            for its in range(0, maxIter):
                tempcurr = tempinit * math.pow(e, -alpha * time)
                time = time + tIncrement
                # NOTE: modifying any node fields won't be final until you run api.update_node()
                

                # repulsive forces
                for v in range(0, numNodes): # TODO: -1?
                    # TODO: this can help manage stray nodes could add as input option?
                    vNode = allNodes[v]
                    if numReactions > 0:
                        for u in range(0, numNodes):
                            uNode = allNodes[u]
                            if vNode != uNode:
                                delta.x = vNode.position.x - uNode.position.x
                                delta.y = vNode.position.y - uNode.position.y
                                d = math.sqrt(delta.x*delta.x+delta.y*delta.y)
                                if d == 0:
                                    d = 0.001
                                
                                fr = repulsiveForce(d, k)/d
                                #TODO: adjustk = (k * math.log())
                                delta.x = delta.x/d * fr
                                delta.y = delta.y/d * fr 
                                newV = add(Pos[v], delta)
                                newU = minus(Pos[v], delta)
                                Pos[v] = newV
                                Pos[u] = newU
                
                # Attractive forces
                # Calculates attractive forces to the centroids of the reactions
                #print(curs)
                for m in range(0, numReactions): # m keeps track of what reaction we're in
                    cc = curs[m]
                    
                    center = api.compute_centroid(netIn, allReactions[m].sources, allReactions[m].targets)
                    for g in range (0, len(cc)): # g is index inlist of reaction components
                        thisNodeIn = cc[g] # index of node in whole network
                        thisNode = api.get_node_by_index(netIn, thisNodeIn)
                        delta.x = thisNode.position.x - center.x
                        delta.y = thisNode.position.y - center.y
                        d = math.sqrt(delta.x*delta.x+delta.y*delta.y)
                        if (d != 0):
                            #TODO: adjustk
                            fa = attractiveForce(d, k)/d
                            delta.x = delta.x/d * fa
                            delta.y = delta.y/d * fa 
                            newM = minus(Pos[thisNodeIn], delta)
                            newCen = add(CentDisp[m], (delta))
                            Pos[thisNodeIn] = newM
                            CentDisp[m] = newCen


                # Use magnetism
                if (useMagnetism):
                    for o in range(0, numReactions): # keeps track of what reaction we are in
                        sources = allReactions[o].sources
                        targets = allReactions[o].targets
                        cc = curs[o]
                        sameRole: bool
                        for curve1 in range(0, len(cc)): # index of curve in list of components 
                            # TODO: method or field for checing role
                            # TODO: locked nodes?
                            for curve2 in range (0, len(cc)): # index of curve in list of components 
                                Node1In = cc[curve1] # index in whole network
                                Node1 = api.get_node_by_index(netIn, Node1In)
                                Node2In = cc[curve2] # index in whole network
                                Node2 = api.get_node_by_index(netIn, Node2In)
            
                                if ((curve1 in sources) and (curve2 in sources)) or ((curve1 in targets) and (curve2 in targets)):
                                    sameRole = True
                                else:
                                    sameRole = False

                                if (curve1 != curve2 and sameRole):
                                    delta.x = Node1.position.x - Node2.position.x
                                    delta.y = Node1.position.y - Node2.position.y
                                    d = math.sqrt(delta.x*delta.x+delta.y*delta.y)
                                    if (d != 0):
                                        #TODO: adjustk use k instead for now
                                        delta.x = (delta.x/d * (d*d/k))/4
                                        delta.y = (delta.x/d * (d*d/k))/4
                                        new1 = minus(Pos[Node1In], delta)
                                        new2 = add(Pos[Node2In], (delta))
                                        Pos[Node1In] = new1
                                        Pos[Node2In] = new2


                # Gravity
                if (gravity > 5):
                    for f in range (0, numNodes):
                        curNode = allNodes[f]
                        # TODO: locked?
                        delta.x = curNode.position.x - baryCenter.x
                        delta.y = curNode.position.y - baryCenter.y
                        d = math.sqrt(delta.x*delta.x+delta.y*delta.y)
                        # TODO: adjustk
                        if (d != 0):
                            delta.x = (delta.x/d * (d*k))
                            delta.y = (delta.x/d * (d*k))
                            newPos = minus(Pos[f], (delta))
                            Pos[Node1In] = newPos



                # Adjust Coordinates
                count = 0
                for curNode in api.get_nodes(0):
                    displ = Pos[count]
                    d = math.sqrt(displ.x*displ.x+displ.y*displ.y)
                    
                    if (d != 0):
                        # canvasCenter = Vec2(canvasSize.x /2, canvasSize.y/2)
                        curPos = curNode.position
                        addPos = PointF(displ.x/d * tempcurr, displ.y/d * tempcurr)
                        newPos = add(curPos, addPos)
                        if (useBoundary):
                            adjustedx = min(canvasSize.x/2, max(-(canvasSize.x/2), newPos.x))
                            adjustedy = min(canvasSize.y/2, max(-(canvasSize.y/2), newPos.y))
                            newPos = PointF(adjustedx, adjustedy)
                        # new = Vec2(newPos.x, newPos.y)
                        # tempPos = minus(curPos, PointF(1,1))
                        #print(a)
                        # indx = api.cur_net_index()
                        if newPos.x >= 0 and newPos.y >= 0:
                            api.update_node(0, curNode.index, position = Vec2(newPos.x, newPos.y))
                    
                    count += 1
                    
                    # TODO: boundary and grid

                its += 1 # TODO: check
                
        canvasSize = api.canvas_size()
        fruchtermanReingold(self, canvasSize)