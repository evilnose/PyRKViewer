"""
Export the network on canvas to an SBML string.
Version 0.01: Author: Jin Xu (2021)
"""


# pylint: disable=maybe-no-member

from inspect import Parameter
from libsbml import KineticLaw
from tesbml.libsbml import BoundaryCondition
import wx
from rkplugin.plugins import PluginMetadata, WindowedPlugin, PluginCategory
from rkplugin import api
from rkplugin.api import Node, Vec2, Reaction, Color
import os
import simplesbml # has to import in the main.py too

class ExportSBML(WindowedPlugin):
    metadata = PluginMetadata(
        name='ExportSBML',
        author='Jin Xu',
        version='0.0.1',
        short_desc='Export SBML.',
        long_desc='Export the SBML String from the network on canvas.',
        category=PluginCategory.ANALYSIS
    )


    def create_window(self, dialog):
        """
        Create a window to do the SBML export.
        Args:
            self
            dialog
        """
        self.window = wx.Panel(dialog, pos=(5,100), size=(300, 320))

        export_btn = wx.Button(self.window, -1, 'Export', (5, 5))
        export_btn.Bind(wx.EVT_BUTTON, self.Export)

        save_btn = wx.Button(self.window, -1, 'Save', (100, 5))
        save_btn.Bind(wx.EVT_BUTTON, self.Save)

        wx.StaticText(self.window, -1, 'SBML string:', (5,30))
        self.SBMLText = wx.TextCtrl(self.window, -1, "", (10, 50), size=(260, 220), style=wx.TE_MULTILINE)
        self.SBMLText.SetInsertionPoint(0)

        return self.window

    def Export(self, evt):
        """
        Handler for the "Export" button.
        Get the network on canvas and change it to an SBML string.
        """
        isReversible = True
        netIn = 0
        numNodes = api.node_count(netIn)
        
        if numNodes == 0:
            wx.MessageBox("Please import a network on canvas", "Message", wx.OK | wx.ICON_INFORMATION)
        else:
            allNodes = api.get_nodes(netIn)
            id = allNodes[0].id[0:-2]
            numReactions = api.reaction_count(netIn)
            allReactions = api.get_reactions(netIn)
            allcompartments = api.get_compartments(netIn)
            numCompartments = len(allcompartments)          

            model = simplesbml.SbmlModel()
            if numCompartments != 0:
                for i in range(numCompartments):    
                    model.addCompartment(allcompartments[i].volume, comp_id=allcompartments[i].id)
                    for j in range(len(allcompartments[i].nodes)):
                        spec_id = allNodes[allcompartments[i].nodes[j]].id
                        if allNodes[allcompartments[i].nodes[j]].floatingNode == False:
                            spec_id = '$' + spec_id
                        # the concentration of the species has been set as 1.0 because the info lack from Nodes
                        model.addSpecies(spec_id, 1.0, comp=allcompartments[i].id)

                for i in range(numReactions):
                    rct = []
                    prd = []

                    rev = False
                    for j in range(len(allReactions[i].sources)):
                        rct.append(allNodes[allReactions[i].sources[j]].id)
                    for j in range(len(allReactions[i].targets)):
                        prd.append(allNodes[allReactions[i].targets[j]].id)

                    rct_num = len(allReactions[i].sources)
                    prd_num = len(allReactions[i].targets)
                    kinetic_law = ''
                    parameter_list = []
                    kinetic_law = kinetic_law + 'E' + str (i) + '*(k' + str (i) 
                    parameter_list.append('E' + str (i))
                    parameter_list.append('k' + str (i))
                    for j in range(rct_num):
                        kinetic_law = kinetic_law + '*' + id + '_' + str (allReactions[i].sources[j])
                    if isReversible:
                        rev = True
                        kinetic_law = kinetic_law + ' - k' + str (i) + 'r'
                        parameter_list.append('k' + str (i) + 'r')
                        for j in range(prd_num):
                            kinetic_law = kinetic_law + '*' + id + '_' + str (allReactions[i].targets[j])
                    kinetic_law = kinetic_law + ')'
                    for j in range(len(parameter_list)):
                        #assuming all the parameters are 0.1
                        model.addParameter(parameter_list[j], 0.1)
                    model.addReaction(rct, prd, kinetic_law, rxn_id=allReactions[i].id)
            else:
                #model.addCompartment(volume=1.0, comp_id='comp')
                for i in range(numNodes):
                    # the concentration of the species has been set as 1.0 because the info lack from Nodes
                    #model.addSpecies(allNodes[i].id, 1.0, comp='comp')
                    spec_id = allNodes[i].id
                    if allNodes[i].floatingNode == False:
                        spec_id = '$' + spec_id
                    model.addSpecies(spec_id, 1.0)

                for i in range(numReactions):
                    rct = []
                    prd = []
                    rev = False
                    for j in range(len(allReactions[i].sources)):
                        rct.append(allNodes[allReactions[i].sources[j]].id)
                    for j in range(len(allReactions[i].targets)):
                        prd.append(allNodes[allReactions[i].targets[j]].id)

                    rct_num = len(allReactions[i].sources)
                    prd_num = len(allReactions[i].targets)
                    kinetic_law = ''
                    parameter_list = []
                    kinetic_law = kinetic_law + 'E' + str (i) + '*(k' + str (i) 
                    parameter_list.append('E' + str (i))
                    parameter_list.append('k' + str (i))
                    for j in range(rct_num):
                        kinetic_law = kinetic_law + '*' + id + '_' + str (allReactions[i].sources[j])
                    if isReversible:
                        rev = True
                        kinetic_law = kinetic_law + ' - k' + str (i) + 'r'
                        parameter_list.append('k' + str (i) + 'r')
                        for j in range(prd_num):
                            kinetic_law = kinetic_law + '*' + id + '_' + str (allReactions[i].targets[j])
                    kinetic_law = kinetic_law + ')'
                    for j in range(len(parameter_list)):
                        #assuming all the parameters are 0.1
                        model.addParameter(parameter_list[j], 0.1)
                    model.addReaction(rct, prd, kinetic_law, rxn_id=allReactions[i].id)

            sbmlStr = str(model)
            self.SBMLText.SetValue(sbmlStr)
           
    def Save(self, evt):
        """
        Handler for the "Save" button.
        Save the SBML string to a file.
        """
        self.dirname=""  #set directory name to blank 
        dlg = wx.FileDialog(self.window, "Save As", self.dirname, wildcard="SBML files (*.xml)|*.xml", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            # Grab the content to be saved
            itcontains = self.SBMLText.GetValue()
            # Open the file for write, write, close
            self.filename=dlg.GetFilename()
            self.dirname=dlg.GetDirectory()
            filehandle=open(os.path.join(self.dirname, self.filename),'w')
            filehandle.write(itcontains)
            filehandle.close()
        # Get rid of the dialog to keep things tidy
        dlg.Destroy()



