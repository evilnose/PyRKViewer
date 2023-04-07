"""
Display a random network.

Version 1.0.1: Author: Jin Xu, Herbert M. Sauro (2020)

"""


import wx
from rkviewer.plugin.classes import PluginMetadata, WindowedPlugin, PluginCategory
from rkviewer.plugin import api
from rkviewer.plugin.api import Node, Vec2, Reaction
import math
import random as _random
import numpy as _np
import copy as _copy
from dataclasses import dataclass
import decimal



@dataclass
class DefaultValues:
    maxSpecies = 15
    maxReactions = 20
    probUniUniValue = 1
    probUniBiValue = 0
    probBiUniValue = 0
    probBiBiValue = 0
    randomSeed = 130


class RandomNetwork(WindowedPlugin):
    metadata = PluginMetadata(
        name='RandomNetwork',
        author='Jin Xu, Herbert M. Sauro',
        version='1.0.1',
        short_desc='Random network.',
        long_desc='Display a random network with certain number of species and reactions as input.',
        category=PluginCategory.MODELS
    )
    def __init__(self):
        """
        Initialize the RandomNetwork.

        Args:
            self

        """
        super().__init__()
        

    def create_window(self, dialog):
        """
        Create a window with several inputs and buttons.
        Args:
            self
            dialog
        """

        window = wx.Panel(dialog, pos=(5,100), size=(300, 320))

        numSpecs = wx.StaticText(window, -1, 'Number of Species:', (20,20))
        self.numSpecsText = wx.TextCtrl(window, -1, str(DefaultValues.maxSpecies), (160, 20), size=(100, -1))
        self.numSpecsText.SetInsertionPoint(0)
        self.numSpecsText.Bind(wx.EVT_TEXT, self.OnText_numSpecs)
        self.numSpecsValue = int(self.numSpecsText.GetValue())
       
        numRxns = wx.StaticText(window, -1, 'Number of Reactions:', (20,50))
        self.numRxnsText = wx.TextCtrl(window, -1, str(DefaultValues.maxReactions), (160, 50), size=(100, -1))
        self.numRxnsText.SetInsertionPoint(0)
        self.numRxnsText.Bind(wx.EVT_TEXT, self.OnText_numRxns)
        self.numRxnsValue = int(self.numRxnsText.GetValue())  
 
        probUniUni = wx.StaticText(window, -1, 'Probability of UniUni:', (20,90))      
        self.probUniUniText = wx.TextCtrl(window, -1, str(DefaultValues.probUniUniValue), (160, 90), size=(100, -1))
        self.probUniUniText.SetInsertionPoint(0)
        self.probUniUniText.Bind(wx.EVT_TEXT, self.OnText_UniUni)
        self.probUniUniValue = float(self.probUniUniText.GetValue())        
 
        probBiUni = wx.StaticText(window, -1, 'Probability of BiUni:', (20,120))
        self.probBiUniText = wx.TextCtrl(window, -1, str(DefaultValues.probBiUniValue), (160, 120), size=(100, -1))
        self.probBiUniText.SetInsertionPoint(0)
        self.probBiUniText.Bind(wx.EVT_TEXT, self.OnText_BiUni)
        self.probBiUniValue = float(self.probBiUniText.GetValue())

        probUniBi = wx.StaticText(window, -1, 'Probability of UniBi:', (20,150))
        self.probUniBiText = wx.TextCtrl(window, -1, str(DefaultValues.probUniBiValue), (160, 150), size=(100, -1))
        self.probUniBiText.SetInsertionPoint(0)
        self.probUniBiText.Bind(wx.EVT_TEXT, self.OnText_UniBi)
        self.probUniBiValue = float(self.probUniBiText.GetValue())

        probBiBi = wx.StaticText(window, -1, 'Probability of BiBi:', (20,180))
        self.probBiBiText = wx.TextCtrl(window, -1, str(DefaultValues.probBiBiValue), (160, 180), size=(100, -1))
        self.probBiBiText.SetInsertionPoint(0)
        self.probBiBiText.Bind(wx.EVT_TEXT, self.OnText_BiBi)
        self.probBiBiValue = float(self.probBiBiText.GetValue())

        randomSeed = wx.StaticText(window, -1, 'Random seed:', (20,210))
        randomSeed = wx.StaticText(window, -1, '0 means no seed setup', (20,230))
        self.randomSeedText = wx.TextCtrl(window, -1, str(DefaultValues.randomSeed), (160, 210), size=(100, -1))
        self.randomSeedText.SetInsertionPoint(0)
        self.randomSeedText.Bind(wx.EVT_TEXT, self.OnText_randomSeed)
        self.randomSeedValue = float(self.randomSeedText.GetValue())
 
        apply_btn = wx.Button(window, -1, 'Apply', (160, 250))
        apply_btn.Bind(wx.EVT_BUTTON, self.Apply)

        return window


    def OnText_numSpecs(self, evt):
        update = evt.GetString()
        if update != '':
            try:
                self.numSpecsValue = int(self.numSpecsText.GetValue())
            except:
                wx.MessageBox("Please enter an integer for the number of species.", "Message", wx.OK | wx.ICON_INFORMATION)


    def OnText_numRxns(self, evt):
        update = evt.GetString()
        if update != '':
            try:
                self.numRxnsValue = int(self.numRxnsText.GetValue())
            except:
                wx.MessageBox("Please enter an integer for the number of reactions.", "Message", wx.OK | wx.ICON_INFORMATION)

 
    def OnText_UniUni(self, evt):
        update = evt.GetString()
        if update != '':
            try:
                self.probUniUniValue = float(self.probUniUniText.GetValue())
            except:
                wx.MessageBox("Please enter a floating point number for the probability of UniUni.", "Message", wx.OK | wx.ICON_INFORMATION)


    def OnText_BiUni(self, evt):
        update = evt.GetString()
        if update != '':
            #DefaultValues.probBiUniValue = float(self.probBiUniText.GetValue())
            try:
                self.probBiUniValue = float(self.probBiUniText.GetValue())
            except:
                wx.MessageBox("Please enter a floating point number for the probability of BiUni.", "Message", wx.OK | wx.ICON_INFORMATION)

    def OnText_UniBi(self, evt):
        update = evt.GetString()
        if update != '':
            try:
                self.probUniBiValue = float(self.probUniBiText.GetValue())
            except:
                wx.MessageBox("Please enter a floating point number for the probability of UniBi.", "Message", wx.OK | wx.ICON_INFORMATION)


    def OnText_BiBi(self, evt):
        update = evt.GetString()
        if update != '':
            try:
                self.probBiBiValue = float(self.probBiBiText.GetValue())
            except:
                wx.MessageBox("Please enter a floating point number for the probability of BiBi.", "Message", wx.OK | wx.ICON_INFORMATION)

    def OnText_randomSeed(self, evt):
        update = evt.GetString()
        if update != '':
            try:
                self.randomSeedValue = float(self.randomSeedText.GetValue())
            except:
                wx.MessageBox("Please enter a valid random seed other than zero.", "Message", wx.OK | wx.ICON_INFORMATION)


    def Apply(self, evt):
        """
        Handler for the "apply" button. apply the random network.
        """
        if self.randomSeedValue != 0:
            _random.seed(self.randomSeedValue)

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

        decimal.getcontext().prec = 6
        test_prob = decimal.Decimal(self.probUniUniValue) \
                  + decimal.Decimal(self.probBiUniValue) \
                  + decimal.Decimal(self.probUniBiValue) \
                  + decimal.Decimal(self.probBiBiValue)

        if test_prob != 1:
            wx.MessageBox("The sum of probabilities should be one!", "Message", wx.OK | wx.ICON_INFORMATION)

        else:
            net_index = 0
            api.clear_network(net_index)

            rl = _generateReactionList (self.numSpecsValue, self.numRxnsValue)
            st = _getFullStoichiometryMatrix (rl)
            antStr = _getRateLaw (st[1], st[2], rl, isReversible=True)
            numNodes = st.shape[0]
            numRxns = st.shape[1]

            nodeIdx = []
            for i in range (numNodes):
                nodeIdx.append (api.add_node(net_index, 'node_{}'.format(i), size=Vec2(60,40), 
                fill_color=api.Color(255, 204, 153),border_color=api.Color(255, 108, 9),
                position=Vec2(40 + math.trunc (_random.random()*800), 40 + math.trunc (_random.random()*800))))
        
            for i in range (numRxns):
                src = []
                dest = []
            
                for j in range(numNodes):
                    if (st.item(j,i) == -1):
                        src.append(nodeIdx[j])  
                    if (st.item(j,i) == 1):
                        dest.append(nodeIdx[j])
                r_idx = api.add_reaction(net_index, 'reaction_{}'.format(i), src, dest, fill_color=api.Color(91, 176, 253))
            
            # Need to remove orphan nodes
            for i in range (numNodes):
                if _np.array_equal(st[i,:], _np.zeros(numRxns)):
                    api.delete_node(net_index, nodeIdx[i])
        

