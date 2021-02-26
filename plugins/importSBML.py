"""
Import an SBML string from a file and visualize it to a network on canvas.
Version 0.01: Author: Jin Xu (2021)
"""


# pylint: disable=maybe-no-member

from inspect import Parameter
from libsbml import KineticLaw
#from tesbml.libsbml import BoundaryCondition
import wx
from rkplugin.plugins import PluginMetadata, WindowedPlugin, PluginCategory
from rkplugin import api
from rkplugin.api import Node, Vec2, Reaction, Color
import os
import simplesbml # has to import in the main.py too
from libsbml import *
import math
import random as _random

class ExportSBML(WindowedPlugin):
    metadata = PluginMetadata(
        name='ImportSBML',
        author='Jin Xu',
        version='0.0.1',
        short_desc='Import SBML.',
        long_desc='Import an SBML String from a file and visualize it as a network on canvas.',
        category=PluginCategory.ANALYSIS
    )


    def create_window(self, dialog):
        """
        Create a window to import SBML.
        Args:
            self
            dialog
        """
        self.window = wx.Panel(dialog, pos=(5,100), size=(300, 320))
        self.sbmlStr = ''
        import_btn = wx.Button(self.window, -1, 'Import', (5, 5))
        import_btn.Bind(wx.EVT_BUTTON, self.Import)

        visualize_btn = wx.Button(self.window, -1, 'Visualize', (100, 5))
        visualize_btn.Bind(wx.EVT_BUTTON, self.Visualize)

        wx.StaticText(self.window, -1, 'SBML string:', (5,30))
        self.SBMLText = wx.TextCtrl(self.window, -1, "", (10, 50), size=(260, 220), style=wx.TE_MULTILINE)
        self.SBMLText.SetInsertionPoint(0)

        return self.window

    def Import(self, evt):
        """
        Handler for the "Import" button.
        Open the SBML file and show it in the TextCtrl box.
        """
        self.dirname=""  #set directory name to blank
        dlg = wx.FileDialog(self.window, "Choose a file to open", self.dirname, wildcard="SBML files (*.xml)|*.xml", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) #open the dialog boxto open file
        if dlg.ShowModal() == wx.ID_OK:  #if positive button selected....
            self.filename = dlg.GetFilename()  #get the filename of the file
            self.dirname = dlg.GetDirectory()  #get the directory of where file is located
            f = open(os.path.join(self.dirname, self.filename), 'r')  #traverse the file directory and find filename in the OS
            self.sbmlStr = f.read()
            self.SBMLText.SetValue(f.read())  #open the file from location as read
            self.SBMLText.WriteText(self.sbmlStr)
            f.close
        dlg.Destroy()

    def Visualize(self, evt):
        """
        Handler for the "Visualize" button.
        Visualize the SBML string to a network shown on the canvas.
        """

        if len(self.sbmlStr) == 0:
            wx.MessageBox("Please import an SBML file.", "Message", wx.OK | wx.ICON_INFORMATION)

        else:
            net_index = 0
            api.clear_network(net_index)
            comp_id_list = []
            comp_dimension_list = []
            comp_position_list = []
            spec_id_list =[]
            spec_dimension_list =[]
            spec_position_list = []

            ### from here for layout ###
            # change to use libsbml instead of simplesbml
            document = readSBMLFromString(self.sbmlStr)
            model_layout = document.getModel()
            mplugin = (model_layout.getPlugin("layout"))

            if mplugin is None:
                #print(
                #    "[Fatal Error] Layout Extension Level " + layoutns.getLevel() + " Version " + layoutns.getVersion() + " package version " + layoutns.getPackageVersion() + " is not registered.")
                #sys.exit(1)
                wx.MessageBox("There is no layout information, so positions are randomly assigned.", "Message", wx.OK | wx.ICON_INFORMATION)

            #
            # Get the first Layout object via LayoutModelPlugin object.
            #
            else:
                layout = mplugin.getLayout(0)
                if layout is None:
                    wx.MessageBox("There is no layout information, so positions are randomly assigned.", "Message", wx.OK | wx.ICON_INFORMATION)
                else:
                    numCompGlyphs = layout.getNumCompartmentGlyphs()
                    numSpecGlyphs = layout.getNumSpeciesGlyphs()

                    for i in range(numCompGlyphs):
                        compGlyph = layout.getCompartmentGlyph(i)
                        temp_id = compGlyph.getCompartmentId()
                        comp_id_list.append(temp_id)	
                        boundingbox = compGlyph.getBoundingBox()
                        height = boundingbox.getHeight()
                        width = boundingbox.getWidth()
                        pos_x = boundingbox.getX()
                        pos_y = boundingbox.getY()
                        comp_dimension_list.append([width,height])
                        comp_position_list.append([pos_x,pos_y])

                    for i in range(numSpecGlyphs):
                        specGlyph = layout.getSpeciesGlyph(i)
                        spec_id = specGlyph.getSpeciesId()
                        spec_id_list.append(spec_id)
                        boundingbox = specGlyph.getBoundingBox()
                        height = boundingbox.getHeight()
                        width = boundingbox.getWidth()
                        pos_x = boundingbox.getX()
                        pos_y = boundingbox.getY()
                        spec_dimension_list.append([width,height])
                        spec_position_list.append([pos_x,pos_y])

            model = simplesbml.loadSBMLStr(self.sbmlStr)
            
            numFloatingNodes  = model.getNumFloatingSpecies()
            FloatingNodes_ids = model.getListOfFloatingSpecies()
            numBoundaryNodes  = model.getNumBoundarySpecies()
            BoundaryNodes_ids = model.getListOfBoundarySpecies() 
            numRxns   = model.getNumReactions()
            Rxns_ids  = model.getListOfReactionIds()
            numComps  = model.getNumCompartments()
            Comps_ids = model.getListOfCompartmentIds()
            numNodes = numFloatingNodes + numBoundaryNodes


            # add_compartment(net_index: int, id: str, fill_color: Color = None, border_color: Color = None,
            #     border_width: float = None, position: Vec2 = None, size: Vec2 = None,
            #     volume: float = None, nodes: List[int] = None) 

            #layout info: position, size, can not add nodes

            for i in range(numComps):
                temp_id = Comps_ids[i]
                vol= model.getCompartmentVolume(i)
                if len(comp_id_list) != 0:
                    for j in range(numComps):
                        if comp_id_list[j] == temp_id:
                            dimension = comp_dimension_list[j]
                            position = comp_position_list[j]
                else:# no layout info about compartment,
                     # then the whole size of the canvas is the compartment size
                    dimension = [4000,2500]
                    position = [0,0] 

                comp_idx = api.add_compartment(net_index, id=temp_id, volume = vol,
                size=Vec2(dimension[0],dimension[1]),position=Vec2(position[0],position[1]))


            # add_node(net_index: int, id: str, fill_color: Color = None, border_color: Color = None,
            #     border_width: float = None, position: Vec2 = None, size: Vec2 = None, floatingNode: bool = True, lockNode: bool = False)

            # layout info: position, size
            # compartment might need to add first instead of adding nodes first

            comp_node_list = [0]*numComps

            for i in range(numComps):
                comp_node_list[i] = []

            if len(comp_id_list) != 0:
                for i in range (numFloatingNodes):
                    temp_id = FloatingNodes_ids[i]
                    comp_id = model.getCompartmentIdSpeciesIsIn(temp_id)
                    for j in range(numNodes):
                        if temp_id == spec_id_list[j]:
                            dimension = spec_dimension_list[j]
                            position = spec_position_list[j] 
                    nodeIdx_temp = api.add_node(net_index, id=temp_id, size=Vec2(dimension[0],dimension[1]), floatingNode = True, 
                    position=Vec2(position[0],position[1]))
                    for j in range(numComps):
                        if comp_id == comp_id_list[j]:
                            comp_node_list[j].append(nodeIdx_temp)

                for i in range (numBoundaryNodes):
                    temp_id = BoundaryNodes_ids[i]
                    comp_id = model.getCompartmentIdSpeciesIsIn(temp_id)
                    for j in range(numNodes):
                        if temp_id == spec_id_list[j]:
                            dimension = spec_dimension_list[j]
                            position = spec_position_list[j] 
                    nodeIdx_temp = api.add_node(net_index, id=temp_id, size=Vec2(dimension[0],dimension[1]), floatingNode = True, 
                    position=Vec2(position[0],position[1]))
                    for j in range(numComps):
                        if comp_id == comp_id_list[j]:
                            comp_node_list[j].append(nodeIdx_temp)

            else: # there is no layout information, assign position randomly and size as default
                comp_id_list = Comps_ids

                for i in range (numFloatingNodes):
                    temp_id = FloatingNodes_ids[i]
                    comp_id = model.getCompartmentIdSpeciesIsIn(temp_id)
                    nodeIdx_temp = api.add_node(net_index, id=temp_id, size=Vec2(60,40), floatingNode = True, 
                    position=Vec2(40 + math.trunc (_random.random()*800), 40 + math.trunc (_random.random()*800)))
                    for j in range(numComps):
                        if comp_id == comp_id_list[j]:
                            comp_node_list[j].append(nodeIdx_temp)

                for i in range (numBoundaryNodes):
                    temp_id = BoundaryNodes_ids[i]
                    comp_id = model.getCompartmentIdSpeciesIsIn(temp_id)
                    nodeIdx_temp = api.add_node(net_index, id=temp_id, size=Vec2(60,40), floatingNode = False, 
                    position=Vec2(40 + math.trunc (_random.random()*800), 40 + math.trunc (_random.random()*800)))
                    for j in range(numComps):
                        if comp_id == comp_id_list[j]:
                            comp_node_list[j].append(nodeIdx_temp)


            # set_compartment_of_node(net_index: int, node_index: int, comp_index: int)
            for i in range(numComps):
                temp_id = Comps_ids[i]
                for j in range(numComps):
                    if comp_id_list[j] == temp_id:
                        node_list_temp = comp_node_list[j]
                for j in range(len(node_list_temp)):
                    api.set_compartment_of_node(net_index=net_index, node_index=node_list_temp[j], comp_index=i)

            
            # add_reaction(net_index: int, id: str, reactants: List[int], products: List[int],
            #     fill_color: Color = None, line_thickness: float = None,
            #     rate_law: str = '', handle_positions: List[Vec2] = None,
            #     center_pos: Vec2 = None, use_bezier: bool = True)
 
            #handle_positions, center_pos was set as the default

            numNodes = api.node_count(net_index)
            allNodes = api.get_nodes(net_index)

            for i in range (numRxns):
                src = []
                dst = []
                temp_id = Rxns_ids[i]
                kinetics = model.getRateLaw(i)
                rct_num = model.getNumReactants(i)
                prd_num = model.getNumProducts(i)


                for j in range(rct_num):
                    rct_id = model.getReactant(temp_id,j)
                    for k in range(numNodes):
                        if allNodes[k].id == rct_id:
                            src.append(allNodes[k].index)


                for j in range(prd_num):
                    prd_id = model.getProduct(temp_id,j)
                    for k in range(numNodes):
                        if allNodes[k].id == prd_id:
                            dst.append(allNodes[k].index)


                r_idx = api.add_reaction(net_index, id = temp_id, reactants = src, products = dst,
                rate_law = kinetics)
            

                