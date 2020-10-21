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


@dataclass
class TPointF:   # A 2D point
     x : float
     y : float


metadata = PluginMetadata(
    name='RandomNetwork',
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
        self.nodeCount = 0
        self.rxnCount = 0


    def create_window(self, dialog):
        """
        Create a window with several inputs and buttons.
        Args:
            self
            dialog
        """

        window = wx.Window(dialog, size=(300, 400))

        numSpecs = wx.StaticText(window, -1, 'Number of Species:', (20,20))
        self.numSpecsText = wx.TextCtrl(window, -1, "10", (160, 20), size=(100, -1))
        self.numSpecsText.SetInsertionPoint(0)
        self.numSpecsText.Bind(wx.EVT_TEXT, self.OnText_numSpecs)
        self.numSpecsValue = int(self.numSpecsText.GetValue())
        
        numRxns = wx.StaticText(window, -1, 'Number of Reactions:', (20,50))
        self.numRxnsText = wx.TextCtrl(window, -1, "2", (160, 50), size=(100, -1))
        self.numRxnsText.SetInsertionPoint(0) 
        self.numRxnsText.Bind(wx.EVT_TEXT, self.OnText_numRxns)
        self.numRxnsValue = int(self.numRxnsText.GetValue())   
 
        probUniUni = wx.StaticText(window, -1, 'Probability of UniUni:', (20,90))      
        self.probUniUniText = wx.TextCtrl(window, -1, "0.25", (160, 90), size=(100, -1))
        self.probUniUniText.SetInsertionPoint(0)
        self.probUniUniText.Bind(wx.EVT_TEXT, self.OnText_UniUni)
        self.probUniUniValue = float(self.probUniUniText.GetValue())        
 
        probBiUni = wx.StaticText(window, -1, 'Probability of BiUni:', (20,120))
        self.probBiUniText = wx.TextCtrl(window, -1, "0.25", (160, 120), size=(100, -1))
        self.probBiUniText.SetInsertionPoint(0)
        self.probBiUniText.Bind(wx.EVT_TEXT, self.OnText_BiUni)
        self.probBiUniValue = float(self.probBiUniText.GetValue())

        probUniBi = wx.StaticText(window, -1, 'Probability of UniBi:', (20,150))
        self.probUniBiText = wx.TextCtrl(window, -1, "0.25", (160, 150), size=(100, -1))
        self.probUniBiText.SetInsertionPoint(0)
        self.probUniBiText.Bind(wx.EVT_TEXT, self.OnText_UniBi)
        self.probUniBiValue = float(self.probUniBiText.GetValue())

        probBiBi = wx.StaticText(window, -1, 'Probability of BiBi:', (20,180))
        self.probBiBiText = wx.TextCtrl(window, -1, "0.25", (160, 180), size=(100, -1))
        self.probBiBiText.SetInsertionPoint(0)
        self.probBiBiText.Bind(wx.EVT_TEXT, self.OnText_BiBi)
        self.probBiBiValue = float(self.probBiBiText.GetValue())
 
        apply_btn = wx.Button(window, -1, 'Apply', (160, 240))
        apply_btn.Bind(wx.EVT_BUTTON, self.Apply)


        return window



    def OnText_numSpecs(self, evt):
        update = evt.GetString()
        if update != '':
            self.numSpecsValue = int(self.numSpecsText.GetValue())

    def OnText_numRxns(self, evt):
        update = evt.GetString()
        if update != '':
            self.numRxnsValue = int(self.numRxnsText.GetValue())
 
    def OnText_UniUni(self, evt):
        update = evt.GetString()
        if update != '':
            self.probUniUniValue = float(self.probUniUniText.GetValue())

    def OnText_BiUni(self, evt):
        update = evt.GetString()
        if update != '':
            self.probBiUniValue = float(self.probBiUniText.GetValue())

    def OnText_UniBi(self, evt):
        update = evt.GetString()
        if update != '':
            self.probUniBiValue = float(self.probUniBiText.GetValue())

    def OnText_BiBi(self, evt):
        update = evt.GetString()
        if update != '':
            self.probBiBiValue = float(self.probBiBiText.GetValue())


    def Apply(self, evt):
        """
        Handler for the "apply" button. apply the random network.
        """
        class _TReactionType:
            UNIUNI = 0
            BIUNI = 1
            UNIBI = 2
            BIBI = 3

        def _pickReactionType():

            rt = _random.random()
            if rt < self.probUniUniValue:
                return _TReactionType.UNIUNI
            elif rt < self.probUniUniValue + self.probBiUniValue:
                return _TReactionType.BIUNI
            elif rt < self.probUniUniValue + self.probBiUniValue + self.probUniBiValue:
                return _TReactionType.UNIBI
            else:
                return _TReactionType.BIBI


        # Generates a reaction network in the form of a reaction list
        # reactionList = [nSpecies, reaction, reaction, ....]
        # reaction = [reactionType, [list of reactants], [list of products], rateConsta>
        # Disallowed reactions:
        # S1 -> S1
        # S1 + S2 -> S2  # Can't have the same reactant and product
        # S1 + S1 -> S1
        def _generateReactionList (nSpecies, nReactions):

            reactionList = []
            for r in range(nReactions):
        
                rateConstant = _random.random()
                rt = _pickReactionType()
                if rt ==  _TReactionType.UNIUNI:
                    # UniUni
                    reactant = _random.randint (0, nSpecies-1)
                    product = _random.randint (0, nSpecies-1)
                    # Disallow S1 -> S1 type of reaction
                    while product == reactant:
                        product = _random.randint (0, nSpecies-1)
                    reactionList.append ([rt, [reactant], [product], rateConstant]) 
               
                if rt ==  _TReactionType.BIUNI:
                    # BiUni
                    # Pick two reactants
                    reactant1 = _random.randint (0, nSpecies-1)
                    reactant2 = _random.randint (0, nSpecies-1)
                
                    # pick a product but only products that don't include the reactants
                    species = range (nSpecies)
                    # Remove reactant1 and 2 from the species list
                    species = _np.delete (species, [reactant1, reactant2], axis=0)
                    # Then pick a product from the reactants that are left
                    product = species[_random.randint (0, len (species)-1)]
               
                    reactionList.append ([rt, [reactant1, reactant2], [product], rateConstant]) 

                if rt ==  _TReactionType.UNIBI:
                    # UniBi
                    reactant1 = _random.randint (0, nSpecies-1)
           
                
                    # pick a product but only products that don't include the reactant
                    species = range (nSpecies)
                    # Remove reactant1 from the species list
                    species = _np.delete (species, [reactant1], axis=0)
                    # Then pick a product from the reactants that are left
                    product1 = species[_random.randint (0, len (species)-1)]
                    product2 = species[_random.randint (0, len (species)-1)]
    
                    reactionList.append ([rt, [reactant1], [product1, product2], rateConstant]) 

                if rt ==  _TReactionType.BIBI:
                    # BiBi
                    reactant1 = _random.randint (0, nSpecies-1)
                    reactant2= _random.randint (0, nSpecies-1)
                
                    # pick a product but only products that don't include the reactant
                    species = range (nSpecies)
                    # Remove reactant1 and 2 from the species list
                    species = _np.delete (species, [reactant1, reactant2], axis=0)
                    # Then pick a product from the reactants that are left
                    product1 = species[_random.randint (0, len (species)-1)]
                    product2 = species[_random.randint (0, len (species)-1)]
               
                    element = [rt, [reactant1, reactant2], [product1, product2], rateConstant]
                    reactionList.append (element)            

            reactionList.insert (0, nSpecies)
            return reactionList



        # Includes boundary and floating species
        # Returns a list:
        # [New Stoichiometry matrix, list of floatingIds, list of boundaryIds]
        def _getFullStoichiometryMatrix (reactionList):
     
            nSpecies = reactionList[0]
            reactionListCopy = _copy.deepcopy (reactionList)
            reactionListCopy.pop (0)
            st = _np.zeros ((nSpecies, len(reactionListCopy)))
    
            for index, r in enumerate (reactionListCopy):
                if r[0] ==  _TReactionType.UNIUNI:
                    # UniUni
                    reactant = reactionListCopy[index][1][0]
                    st[reactant, index] = -1
                    product = reactionListCopy[index][2][0]
                    st[product, index] = 1
     
                if r[0] ==  _TReactionType.BIUNI:
                    # BiUni
                    reactant1 = reactionListCopy[index][1][0]
                    st[reactant1, index] = -1
                    reactant2 = reactionListCopy[index][1][1]
                    st[reactant2, index] = -1
                    product = reactionListCopy[index][2][0]
                    st[product, index] = 1

                if r[0] ==  _TReactionType.UNIBI:
                    # UniBi
                    reactant1 = reactionListCopy[index][1][0]
                    st[reactant1, index] = -1
                    product1 = reactionListCopy[index][2][0]
                    st[product1, index] = 1
                    product2 = reactionListCopy[index][2][1]
                    st[product2, index] = 1
 
                if r[0] ==  _TReactionType.BIBI:
                    # BiBi
                    reactant1 = reactionListCopy[index][1][0]
                    st[reactant1, index] = -1
                    reactant2 = reactionListCopy[index][1][1]
                    st[reactant2, index] = -1
                    product1 = reactionListCopy[index][2][0]
                    st[product1, index] = 1
                    product2 = reactionListCopy[index][2][1]
                    st[product2, index] = 1

            return st 

        def _getRateLaw (floatingIds, boundaryIds, reactionList, isReversible):
    
            nSpecies = reactionList[0]
            # Remove the first element which is the nSpecies
            reactionListCopy = _copy.deepcopy (reactionList)
            reactionListCopy.pop (0)

            antStr_tot = []

            for index, r in enumerate (reactionListCopy):
                antStr= ''
                antStr = antStr + 'J' + str (index) + ': '
                if r[0] == _TReactionType.UNIUNI:
                    # UniUni
                    antStr = antStr + '(k' + str (index) + '*S' + str (reactionListCopy[index][1][0])
                    if isReversible:
                        antStr = antStr + ' - k' + str (index) + 'r' + '*S' + str (reactionListCopy[index][2][0])
                    antStr = antStr + ')'
                if r[0] == _TReactionType.BIUNI:
                    # BiUni
                    antStr = antStr + '(k' + str (index) + '*S' + str (reactionListCopy[index][1][0]) + '*S' + str (reactionListCopy[index][1][1])
                    if isReversible:
                        antStr = antStr + ' - k' + str (index) + 'r' + '*S' + str (reactionListCopy[index][2][0])
                    antStr = antStr + ')'
                if r[0] == _TReactionType.UNIBI:
                    # UniBi
                    antStr = antStr + '(k' + str (index) + '*S' + str (reactionListCopy[index][1][0])
                    if isReversible:
                        antStr = antStr + ' - k' + str (index) + 'r' + '*S' + str (reactionListCopy[index][2][0]) + '*S' + str (reactionListCopy[index][2][1])
                    antStr = antStr + ')'
                if r[0] == _TReactionType.BIBI:
                    # BiBi
                    antStr = antStr + '(k' + str (index) + '*S' + str (reactionListCopy[index][1][0]) + '*S' + str (reactionListCopy[index][1][1])
                    if isReversible:
                        antStr = antStr + ' - k' + str (index) + 'r' + '*S' + str (reactionListCopy[index][2][0]) + '*S' + str (reactionListCopy[index][2][1])
                    antStr = antStr + ')'
                

                antStr_tot.append(antStr)

            return antStr_tot


        def getCenterPt(node):
           #print("print out node:",type(node))
           #position the left down corner, size is the width/height of rectangle
           _x = node.position.x + node.size.x/2
           _y = node.position.y + node.size.y/2
           return(_x,_y)

        def computeCentroid (node1, node2): #enter the list of index of rcts/prds

            # Number of nodes that go into the reaction  
            nSrcNodes = len(node1)
            # Number of nodes that come off the arc
            nDestNodes = len(node2)

            # Calculate the centroid from the nodes associated with the reaction
            arcCentre = TPointF(0, 0)

            for i in range (nSrcNodes):  
                pt = getCenterPt (api.get_node_by_index(0,node1[i]))
                arcCentre.x = arcCentre.x + pt[0]
                arcCentre.y = arcCentre.y + pt[1]

            for i in range (nDestNodes):
                pt = getCenterPt (api.get_node_by_index(0,node2[i]))
                arcCentre.x = arcCentre.x + pt[0]
                arcCentre.y = arcCentre.y + pt[1] 

            totalNodes = nSrcNodes + nDestNodes
            return TPointF (arcCentre.x / totalNodes, arcCentre.y / totalNodes)
            

        numNodes = self.numSpecsValue
        numRxns = self.numRxnsValue

        rl = _generateReactionList (numNodes, numRxns)
        st = _getFullStoichiometryMatrix (rl)
        antStr = _getRateLaw (st[1], st[2], rl, isReversible=True)
        
        net_index = 0
        for i in range (numNodes):
            node = Node(
                   'node_{}'.format(self.nodeCount),
                   pos=Vec2(40 + math.trunc (_random.random()*600), 40 + math.trunc (_random.random()*600)),
                   size=Vec2(60, 40),
                   fill_color=wx.Colour (255,204,153,255),
                   border_color=wx.Colour (255, 102, 0, 255),
                   border_width=2,
                )
            # add the node
            api.add_node(net_index, node)
            self.nodeCount = self.nodeCount + 1
        
        for i in range (numRxns):
            src = []
            dest = []
            
            for j in range(numNodes):
                if (st.item(j,i) == -1):
                    src.append(j)   
                if (st.item(j,i) == 1):
                    dest.append(j)

            position_src  = []
            position_dest = [] 
            for j in range(len(src)):
                position_src.append(api.get_node_by_index (net_index,src[j]).position)

            for j in range(len(dest)):
                position_dest.append(api.get_node_by_index (net_index,dest[j]).position)
            
            self.arcCenter = computeCentroid (src, dest)
            cx = self.arcCenter.x
            cy = self.arcCenter.y
            position_centroid = (cx, cy)
           
            handle_Vec2_list = [Vec2(cx,cy)]
            for j in range(len(src)):
                x = (position_centroid[0]+position_src[j][0])/2
                y = (position_centroid[1]+position_src[j][1])/2
                handle_Vec2_list.append(Vec2(x,y))
            for j in range(len(dest)):
                x = (position_centroid[0]+position_dest[j][0])/2
                y = (position_centroid[1]+position_dest[j][1])/2
                handle_Vec2_list.append(Vec2(x,y))

            reaction = Reaction(
                       'reaction_{}'.format(self.rxnCount),
                       sources=src, #list
                       targets=dest, #list
                       #the len of handle_position = len(src) + len(dest) + 1
                       #centroid, substrate(rcts), prds
                       handle_positions=handle_Vec2_list,
                       fill_color=wx.BLUE,
                       line_thickness=3,
                       rate_law=antStr[i]
                    )

            # add the reaction
            api.add_reaction(0, reaction)
      
            self.rxnCount = self.rxnCount + 1



