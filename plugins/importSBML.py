"""
Import an SBML string from a file and visualize it to a network on canvas.
Version 0.02: Author: Jin Xu (2021)
"""


# pylint: disable=maybe-no-member

from inspect import Parameter
from libsbml import KineticLaw
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
        version='0.0.2',
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

        def hex_to_rgb(value):
            value = value.lstrip('#')
            return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))      

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


            #set the default values without render info:
            comp_fill_color = (158, 169, 255)
            comp_border_color = (0, 29, 255)
            comp_border_width = 2.0
            spec_fill_color = (255, 204, 153)
            spec_border_color = (255, 108, 9)
            spec_border_width = 2.0
            reaction_line_color = (129, 123, 255)
            reaction_line_width = 3.0

            ### from here for layout ###
            document = readSBMLFromString(self.sbmlStr)
            model_layout = document.getModel()
            mplugin = (model_layout.getPlugin("layout"))

            if mplugin is None:
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

                    rPlugin = layout.getPlugin("render")
                    if (rPlugin != None and rPlugin.getNumLocalRenderInformationObjects() > 0):
                        info = rPlugin.getRenderInformation(0)
                        color_list = []
                        for  j in range ( 0, info.getNumColorDefinitions()):
                            color = info.getColorDefinition(j)			  
                            color_list.append([color.getId(),color.createValueString()])
                        for j in range (0, info.getNumStyles()):
                            style = info.getStyle(j)
                            group = style.getGroup()
                            typeList = style.createTypeString()
                            if 'COMPARTMENTGLYPH' in typeList:
                                for k in range(len(color_list)):
                                    if color_list[k][0] == group.getFill():
                                        comp_fill_color = hex_to_rgb(color_list[k][1])
                                    if color_list[k][0] == group.getStroke():
                                        comp_border_color = hex_to_rgb(color_list[k][1])
                                comp_border_width = group.getStrokeWidth()
                            elif 'SPECIESGLYPH' in typeList:
                                for k in range(len(color_list)):
                                    if color_list[k][0] == group.getFill():
                                        spec_fill_color = hex_to_rgb(color_list[k][1])
                                    if color_list[k][0] == group.getStroke():
                                        spec_border_color = hex_to_rgb(color_list[k][1])
                                spec_border_width = group.getStrokeWidth()
                            elif 'REACTIONGLYPH' in typeList:
                                for k in range(len(color_list)):
                                    if color_list[k][0] == group.getStroke():
                                        reaction_line_color = hex_to_rgb(color_list[k][1])
                                reaction_line_width = group.getStrokeWidth()


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

            for i in range(numComps):
                temp_id = Comps_ids[i]
                vol= model.getCompartmentVolume(i)
                if len(comp_id_list) != 0:
                #if mplugin is not None:
                    for j in range(numComps):
                        if comp_id_list[j] == temp_id:
                            dimension = comp_dimension_list[j]
                            position = comp_position_list[j]
                else:# no layout info about compartment,
                     # then the whole size of the canvas is the compartment size
                    dimension = [4000,2500]
                    position = [0,0] 

                api.add_compartment(net_index, id=temp_id, volume = vol,
                size=Vec2(dimension[0],dimension[1]),position=Vec2(position[0],position[1]),
                fill_color = api.Color(comp_fill_color[0],comp_fill_color[1],comp_fill_color[2]),
                border_color = api.Color(comp_border_color[0],comp_border_color[1],comp_border_color[2]),
                border_width = comp_border_width)


            comp_node_list = [0]*numComps

            for i in range(numComps):
                comp_node_list[i] = []

            if len(comp_id_list) != 0:
            #if mplugin is not None:
                for i in range (numFloatingNodes):
                    temp_id = FloatingNodes_ids[i]
                    comp_id = model.getCompartmentIdSpeciesIsIn(temp_id)
                    for j in range(numNodes):
                        if temp_id == spec_id_list[j]:
                            dimension = spec_dimension_list[j]
                            position = spec_position_list[j] 
                    nodeIdx_temp = api.add_node(net_index, id=temp_id, floatingNode = True, 
                    size=Vec2(dimension[0],dimension[1]), position=Vec2(position[0],position[1]), 
                    fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2]),
                    border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2]),
                    border_width=spec_border_width)
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
                    nodeIdx_temp = api.add_node(net_index, id=temp_id, floatingNode = False, 
                    size=Vec2(dimension[0],dimension[1]), position=Vec2(position[0],position[1]), 
                    fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2]),
                    border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2]),
                    border_width=spec_border_width)
                    for j in range(numComps):
                        if comp_id == comp_id_list[j]:
                            comp_node_list[j].append(nodeIdx_temp)

            else: # there is no layout information, assign position randomly and size as default
                comp_id_list = Comps_ids

                for i in range (numFloatingNodes):
                    temp_id = FloatingNodes_ids[i]
                    comp_id = model.getCompartmentIdSpeciesIsIn(temp_id)
                    nodeIdx_temp = api.add_node(net_index, id=temp_id, size=Vec2(60,40), floatingNode = True, 
                    position=Vec2(40 + math.trunc (_random.random()*800), 40 + math.trunc (_random.random()*800)),
                    fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2]),
                    border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2]),
                    border_width=spec_border_width)
                    for j in range(numComps):
                        if comp_id == comp_id_list[j]:
                            comp_node_list[j].append(nodeIdx_temp)

                for i in range (numBoundaryNodes):
                    temp_id = BoundaryNodes_ids[i]
                    comp_id = model.getCompartmentIdSpeciesIsIn(temp_id)
                    nodeIdx_temp = api.add_node(net_index, id=temp_id, size=Vec2(60,40), floatingNode = False, 
                    position=Vec2(40 + math.trunc (_random.random()*800), 40 + math.trunc (_random.random()*800)),
                    fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2]),
                    border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2]),
                    border_width=spec_border_width)
                    for j in range(numComps):
                        if comp_id == comp_id_list[j]:
                            comp_node_list[j].append(nodeIdx_temp)


            for i in range(numComps):
                temp_id = Comps_ids[i]
                for j in range(numComps):
                    if comp_id_list[j] == temp_id:
                        node_list_temp = comp_node_list[j]
                for j in range(len(node_list_temp)):
                    api.set_compartment_of_node(net_index=net_index, node_index=node_list_temp[j], comp_index=i)

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

                api.add_reaction(net_index, id=temp_id, reactants=src, products=dst, rate_law = kinetics,
                fill_color=api.Color(reaction_line_color[0],reaction_line_color[1],reaction_line_color[2]), 
                line_thickness=reaction_line_width)
            

                