'''
Given a random network, this plugin  will rearrange the network neatly on the screen.
Version 1.0.3: Author: Carmen Perena Cortes, Herbert M. Sauro, Jin Xu, 2022
Based on THOMAS M. J. FRUCHTERMAN AND EDWARD M. REINGOLD's Graph Drawing by Force-directed Placement
SOFTWARE - PRACTICE AND EXPERIENCE, VOL. 21(1 1), 1129-1164 (NOVEMBER 1991)
Using python's networkx
'''
# pylint: disable=maybe-no-member
import wx
from rkviewer.plugin.classes import PluginMetadata, WindowedPlugin, PluginCategory
from rkviewer.plugin import api
from rkviewer.plugin.api import Node, Vec2, Reaction, get_reaction_by_index
import math
from dataclasses import field
from typing import List
from random import uniform
from numpy.random import rand
import numpy as np
import random
from dataclasses import dataclass
import networkx as nx
import rkviewer.canvas.utils as cu

class LayoutNetworkX(WindowedPlugin):
    metadata = PluginMetadata(
        name='AutoLayout',
        author='Carmen Perena Cortes, Herbert M. Sauro and Jin Xu',
        version='1.0.3',
        short_desc='Auto Layout using networkX.',
        long_desc='Rearrange a random network into a neat auto layout',
        category=PluginCategory.VISUALIZATION,
    )

    def create_window(self, dialog):
        '''
        Create a window with several inputs and buttons.
        Args:
            self
            dialog
        '''
        # TODO: k, gravity, useMagnetism, useBoundary, useGrid
        self.window = wx.Panel(dialog, pos=(5,100), size=(350, 220))
        self.sizer = wx.FlexGridSizer(cols=2, vgap=10, hgap=0)
        self.sizer.AddGrowableCol(0, int(0.6))
        self.sizer.AddGrowableCol(1, int(0.4))

        self.sizer.Add((0, 10))
        self.sizer.Add((0, 10))

        self.MaxIterText = wx.TextCtrl(self.window, -1, "100", size=(100, -1))
        self.MaxIterText.SetInsertionPoint(0)
        self.MaxIterText.Bind(wx.EVT_TEXT, self.OnText_MaxIter)
        self.MaxIterValue = int(self.MaxIterText.GetValue())
        self.AddField('Max Number of Iterations', self.MaxIterText)

        self.kText = wx.TextCtrl(self.window, -1, "70", size=(100, -1))
        self.kText.SetInsertionPoint(0)
        self.kText.Bind(wx.EVT_TEXT, self.OnText_k)
        self.kValue = float(self.kText.GetValue())
        self.AddField('k (float > 0)', self.kText)

        self.scaleText = wx.TextCtrl(self.window, -1, "550", size=(100, -1))
        self.scaleText.SetInsertionPoint(0)
        self.scaleText.Bind(wx.EVT_TEXT, self.OnText_scale)
        self.scaleValue = float(self.scaleText.GetValue())
        self.AddField('Scale of Layout', self.scaleText)

        self.useCentroid = False
        self.centroidCheckBox = wx.CheckBox(self.window)
        self.centroidCheckBox.Bind(wx.EVT_CHECKBOX, self.OnCheckUseCentroid)
        self.AddField('Also Arrange Centroids', self.centroidCheckBox)

        # add spacer left of button
        self.sizer.Add((0, 0))
        apply_btn = wx.Button(self.window, -1, 'Run', (220, 130))
        apply_btn.Bind(wx.EVT_BUTTON, self.Apply)
        self.sizer.Add(apply_btn)
        self.window.SetPosition (wx.Point(10,10))
        self.window.SetSizer(self.sizer)
        return self.window

    def AddField(self, text, field):
        self.sizer.Add(wx.StaticText(self.window, label=text), wx.SizerFlags().Border(wx.LEFT, 20))
        self.sizer.Add(field)

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

    def OnText_scale(self, evt):
        try:
           update = evt.GetString()
           if update != '':
              self.scaleValue = float(self.scaleText.GetValue())
        except ValueError:
           wx.MessageBox('Value must be a number', 'Error', wx.OK | wx.ICON_INFORMATION)

    def OnCheckUseCentroid(self, evt):
        cb = evt.GetEventObject()
        self.useCentroid = cb.GetValue()

    def Apply(self, evt):
        if api.node_count(0) == 0:
            return
        G = nx.Graph()
        nodesInd = np.array(list(api.get_node_indices(0)))
        reactionsInd =  np.array(list(api.get_reaction_indices(0)))
        originalPos = {}
        def generateGraph():
            # add nodes and centroids as "nodes" for networkX
            nodes = np.array(list(api.get_node_indices(0)))
            #reactionsInd =  np.array(list(api.get_reaction_indices(0)))
            cStr = np.empty_like(reactionsInd, dtype=str)
            cStr[:,] = "c"
            centroidId = np.char.add(cStr, reactionsInd.astype(str))
            G.add_nodes_from(centroidId)
            nStr = np.empty_like(nodes, dtype=str)
            nStr[:,] = "n"
            nodesId = np.array(list(np.char.add(nStr, nodesInd.astype(str))))
            G.add_nodes_from(nodesId)
            '''
            for n in nodes:
                centroidsTo = np.array(list(api.get_reactions_as_product(0, n))) # Gets the reactions in which it is a product -> TO
                cStr = np.empty_like(centroidsTo, dtype=str)
                cStr[:,] = "c"
                centroidsToIn = np.char.add(cStr, centroidsTo.astype(str)) # centroids from which the node is product
                centroidsFrom = np.array(list(api.get_reactions_as_reactant(0, n))) # reactions in which it is a reactanr -> FROM
                cStr = np.empty_like(centroidsFrom, dtype=str)
                cStr[:,] = "c"
                centroidsFromIn = np.char.add(cStr, centroidsFrom.astype(str)) # centroids to which the node is reactant
                nS = np.empty_like(centroidsToIn, dtype = str)
                nS[:,] = "n"
                numS = np.empty_like(centroidsToIn, dtype = int)
                numS[:,] = n
                nodeIndArrayTo = np.char.add(nS, numS.astype(str))
                nS = np.empty_like(centroidsFromIn, dtype = str)
                nS[:,] = "n"
                numS = np.empty_like(centroidsFromIn, dtype = int)
                numS[:,] = n
                nodeIndArrayFrom = np.char.add(nS, numS.astype(str))
                edgesTo = np.array(list(zip(centroidsToIn, nodeIndArrayTo)))
                edgesFrom = np.array(list(zip(nodeIndArrayFrom, centroidsFromIn)))
                G.add_edges_from(edgesTo)
                G.add_edges_from(edgesFrom)
            '''

            # Add edges from reactant to centroid and centroid to product (undirected)
            edges = list()
            for reaction in api.get_reactions(0):
                for s in reaction.sources:
                    edges.append(('n' + str(s), 'c' + str(reaction.index)))
                for t in reaction.targets:
                    edges.append(('c' + str(reaction.index), 'n' + str(t)))

            G.add_edges_from(edges)
            cn = 0
            for rea in api.get_reactions(0):
                cent = api.compute_centroid(0, rea.sources, rea.targets)
                #originalPos[centroidId[cn]] = list([cent.x, cent.y])
                originalPos['c' + str(rea)] = list([random.randint(0,600), random.randint(0,600)])
                cn = cn + 1

            for nod in api.get_nodes(0):
                #originalPos[nodesId[cn]] = list([nod.position.x, nod.position.y])
                # random.randint(0,500), nod.position.y+random.randint (0,500)])
                originalPos['n' + str(nod)] = list([random.randint(0,600), random.randint (0,600)])
                cn = cn + 1
        generateGraph()
        #print(nx.to_dict_of_lists(G))
        #nodeIds = list (api.get_node_indices(0))
        with api.group_action():
            for t in range(1):
                pos = (nx.fruchterman_reingold_layout(G, k = self.kValue, iterations = self.MaxIterValue, scale = self.scaleValue, pos = originalPos, weight=1))
                positions = np.array(list(pos.values()))
                minX = 0
                minY = 0
                for p in positions:
                    if p[0] < minX:
                        minX = p[0]
                    if p[1] < minY:
                        minY = p[1]
                positions = positions - np.array([minX, minY])
                centroids = positions[0: len(reactionsInd)]
                nodes = positions[len(reactionsInd): len(positions)]
                count = 0
                for n in nodes:
                    newX = float(n[0])
                    newY = float(n[1])
                    api.move_node(0, nodesInd[count], position = Vec2(newX, newY), allowNegativeCoordinates=True)
                    count = count + 1

                if self.useCentroid:
                    count = 0
                    for c in centroids:
                        newX = float(c[0])
                        newY = float(c[1])
                        # r = api.get_reaction_by_index(0, reactionsInd[count])
                        # handles = api.default_handle_positions(0, r.index)
                        # api.update_reaction(0, r.index, center_pos=Vec2(newX, newY), handle_positions=handles)
                        index = reactionsInd[count]
                        r = api.get_reaction_by_index(0, index)
                        rcts = r.sources
                        prds = r.targets
                        centroid = Vec2(newX, newY)
                        #update centroid before calculate the default handles
                        # api.update_reaction(0, index, center_pos=Vec2(newX, newY))
                        # handles = api.default_handle_positions(0, r.index)
                        # api.update_reaction(0, index, handle_positions=handles)

                        #set the handles as centroid, except the center_handle, to make all the bezier curves look like straight lines
                      
                        # handles = [centroid]
                        # for x in range(len(rcts)):
                        #     handles.append(centroid)
                        # for y in range(len(prds)):
                        #     handles.append(centroid)
                                 #set the handles, to make all the bezier curves look like straight lines
                        if len(rcts) != 0:
                            spec_pos = api.get_node_by_index(0, rcts[0]).position
                            spec_size = api.get_node_by_index(0, rcts[0]).size
                        else:
                            spec_pos = api.get_node_by_index(0, prds[0]).position
                            spec_size = api.get_node_by_index(0, prds[0]).size
                        center_handle = (0.9*centroid[0]+0.1*(spec_pos[0]+0.5*spec_size[0]), 
                                        0.9*centroid[1]+0.1*(spec_pos[1]+0.5*spec_size[1]))
                        center_handle_vec2 = Vec2(center_handle[0],center_handle[1])
                        #handles = [centroid]
                        handles = [center_handle_vec2]
                        for x in range(len(rcts)):
                            spec_pos = api.get_node_by_index(0, rcts[x]).position
                            spec_size = api.get_node_by_index(0, rcts[x]).size
                            spec_handle = (0.5*(centroid[0]+spec_pos[0]+0.5*spec_size[0]), 
                                        0.5*(centroid[1]+spec_pos[1]+0.5*spec_size[1]))
                            spec_handle_vec2 = Vec2(spec_handle[0],spec_handle[1])
                            handles.append(spec_handle_vec2)
                            #handles.append(centroid)
                        for y in range(len(prds)):
                            spec_pos = api.get_node_by_index(0, prds[y]).position
                            spec_size = api.get_node_by_index(0, prds[y]).size
                            spec_handle = (0.5*(centroid[0]+spec_pos[0]+0.5*spec_size[0]), 
                                        0.5*(centroid[1]+spec_pos[1]+0.5*spec_size[1]))
                            spec_handle_vec2 = Vec2(spec_handle[0],spec_handle[1])
                            handles.append(spec_handle_vec2)
                            #handles.append(centroid)
                        api.update_reaction(0, index, center_pos=Vec2(newX, newY), handle_positions=handles)
                        
                        count = count + 1
                else:
                    for index in api.get_reaction_indices(0):
                        #api.update_reaction(0, index, center_pos=None)
                        #handles = api.default_handle_positions(0, index)
                        #api.update_reaction(0, index, handle_positions=handles)
                        #the following centroid computed is the same as default centroid, or None
                        rcts = get_reaction_by_index(0, index).sources
                        prds = get_reaction_by_index(0, index).targets
                        centroid = api.compute_centroid(0, rcts, prds)
                        #set the handles, to make all the bezier curves look like straight lines
                        if len(rcts) != 0:
                            spec_pos = api.get_node_by_index(0, rcts[0]).position
                            spec_size = api.get_node_by_index(0, rcts[0]).size
                        else:
                            spec_pos = api.get_node_by_index(0, prds[0]).position
                            spec_size = api.get_node_by_index(0, prds[0]).size
                        center_handle = (0.9*centroid[0]+0.1*(spec_pos[0]+0.5*spec_size[0]), 
                                        0.9*centroid[1]+0.1*(spec_pos[1]+0.5*spec_size[1]))
                        center_handle_vec2 = Vec2(center_handle[0],center_handle[1])
                        #handles = [centroid]
                        handles = [center_handle_vec2]
                        for x in range(len(rcts)):
                            spec_pos = api.get_node_by_index(0, rcts[x]).position
                            spec_size = api.get_node_by_index(0, rcts[x]).size
                            spec_handle = (0.5*(centroid[0]+spec_pos[0]+0.5*spec_size[0]), 
                                        0.5*(centroid[1]+spec_pos[1]+0.5*spec_size[1]))
                            spec_handle_vec2 = Vec2(spec_handle[0],spec_handle[1])
                            handles.append(spec_handle_vec2)
                            #handles.append(centroid)
                        for y in range(len(prds)):
                            spec_pos = api.get_node_by_index(0, prds[y]).position
                            spec_size = api.get_node_by_index(0, prds[y]).size
                            spec_handle = (0.5*(centroid[0]+spec_pos[0]+0.5*spec_size[0]), 
                                        0.5*(centroid[1]+spec_pos[1]+0.5*spec_size[1]))
                            spec_handle_vec2 = Vec2(spec_handle[0],spec_handle[1])
                            handles.append(spec_handle_vec2)
                            #handles.append(centroid)
                        api.update_reaction(0, index, center_pos = centroid, handle_positions = handles)

                '''

                for r in api.get_reactions(0):
                    currCentroid = centroids[r.index]
                    newX = float(currCentroid[0])
                    newY = float(currCentroid[1])
                    api.update_reaction(0, r.index, center_pos=(Vec2(newX, newY)))
                    #api.update_reaction(0, r.index, center_pos=None)
                    handles = api.default_handle_positions(0, r.index)
                    api.set_reaction_center_handle(0, r.index, handles[0])
                    count = 1
                    for s in r.sources:
                        api.set_reaction_node_handle(0, r.index, s, True, handles[count])
                        count += 1
                    for t in r.targets:
                        api.set_reaction_node_handle(0, r.index, t, False, handles[count])
                        count += 1

                '''

            ws = api.window_size()
            offset = Vec2(ws.x/4, ws.y/4)
            api.translate_network(0, offset, check_bounds = True)