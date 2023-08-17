"""
Import an SBML string from a file and visualize it to a network on canvas.
Version 1.2.8: Author: Jin Xu (2023)
"""


# pylint: disable=maybe-no-member

from ast import Num
from inspect import Parameter
from ntpath import join
from re import S
import wx
from wx.core import CENTER
from rkviewer.canvas.data import TEXT_POSITION_CHOICES, TextAlignment, TextPosition
from rkviewer.plugin.classes import PluginMetadata, WindowedPlugin, PluginCategory
from rkviewer.plugin import api
from rkviewer.plugin.api import Node, Vec2, Reaction, Color, get_nodes
import os
import simplesbml # does not have to import in the main.py too
from libsbml import *
import math
import random as _random
import pandas as pd
from rkviewer.config import get_theme
import SBMLDiagrams
import re # Extract substrings between brackets
from rkviewer.mvc import ModifierTipStyle

class IMPORTSBML(WindowedPlugin):
    metadata = PluginMetadata(
        name='ImportSBML',
        author='Jin Xu',
        version='1.2.8',
        short_desc='Import SBML.',
        long_desc='Import an SBML String from a file and visualize it as a network on canvas.',
        category=PluginCategory.MODELS
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
        show_btn = wx.Button(self.window, -1, 'Load', (5, 5))
        show_btn.Bind(wx.EVT_BUTTON, self.Show)

        copy_btn = wx.Button(self.window, -1, 'Copy To Clipboard', (83, 5))
        copy_btn.Bind(wx.EVT_BUTTON, self.Copy)

        visualize_btn = wx.Button(self.window, -1, 'Visualize', (205, 5))
        visualize_btn.Bind(wx.EVT_BUTTON, self.Visualize)

        wx.StaticText(self.window, -1, 'SBML string:', (5,30))
        self.SBMLText = wx.TextCtrl(self.window, -1, "", (10, 50), size=(260, 220), style=wx.TE_MULTILINE|wx.HSCROLL)
        self.SBMLText.SetInsertionPoint(0)

        return self.window

    def Show(self, evt):
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

    def Copy(self, evt):
        """
        Handler for the "Copy" button.
        Copy the SBML string to a clipboard.
        """
        self.dataObj = wx.TextDataObject()
        self.dataObj.SetText(self.SBMLText.GetValue())
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(self.dataObj)
            wx.TheClipboard.Close()
        else:
            wx.MessageBox("Unable to open the clipboard", "Error")

    def Visualize(self, evt):
        """
        Handler for the "Visualize" button.
        Visualize the SBML string to a network shown on the canvas.
        """  

        with wx.BusyCursor():
        #with wx.BusyInfo("Please wait, working..."):
            self.DisplayModel(self.sbmlStr, True, False)


    def DisplayModel(self, sbmlStr, showDialogues, useSeed):
        """
        Visualize an SBML string as a network shown on the canvas.
        Args:
          self
          document: SBMLDocument object created from the sbml string
          sbmlStr: sbml string to display
          showDialogues: if false, hides pop-up windows
          useSeed: if true, constant seed for random number generation used,
                   ensuring that different visualizations created from the same
                   file will always have the same layout
        """
        if useSeed:
          _random.seed(13)

        def hex_to_rgb(value):
            value = value.lstrip('#')
            if len(value) == 6:
                value = value + 'ff'
            return tuple(int(value[i:i+2], 16) for i in (0, 2, 4, 6))

        color_data = {"decimal_rgb": ['[240,248,255]', '[250,235,215]', '[0,255,255]', '[127,255,212]', '[240,255,255]', '[245,245,220]', '[255,228,196]', '[0,0,0]', '[255,235,205]', '[0,0,255]', '[138,43,226]', '[165,42,42]', '[222,184,135]', '[95,158,160]', '[127,255,0]', '[210,105,30]', '[255,127,80]', '[100,149,237]', '[255,248,220]', '[220,20,60]', '[0,255,255]', '[0,0,139]', '[0,139,139]', '[184,134,11]', '[169,169,169]', '[0,100,0]', '[189,183,107]', '[139,0,139]', '[85,107,47]', '[255,140,0]', '[153,50,204]', '[139,0,0]', '[233,150,122]', '[143,188,143]', '[72,61,139]', '[47,79,79]', '[0,206,209]', '[148,0,211]', '[255,20,147]', '[0,191,255]', '[105,105,105]', '[30,144,255]', '[178,34,34]', '[255,250,240]', '[34,139,34]', '[255,0,255]', '[220,220,220]', '[248,248,255]', '[255,215,0]', '[218,165,32]', '[128,128,128]', '[0,128,0]', '[173,255,47]', '[240,255,240]', '[255,105,180]', '[205,92,92]', '[75,0,130]', '[255,255,240]', '[240,230,140]', '[230,230,250]', '[255,240,245]', '[124,252,0]', '[255,250,205]', '[173,216,230]', '[240,128,128]', '[224,255,255]', '[250,250,210]', '[144,238,144]', '[211,211,211]', '[255,182,193]', '[255,160,122]', '[32,178,170]', '[135,206,250]', '[119,136,153]', '[176,196,222]', '[255,255,224]', '[0,255,0]', '[50,205,50]', '[250,240,230]', '[255,0,255]', '[128,0,0]', '[102,205,170]', '[0,0,205]', '[186,85,211]', '[147,112,219]', '[60,179,113]', '[123,104,238]', '[0,250,154]', '[72,209,204]', '[199,21,133]', '[25,25,112]', '[245,255,250]', '[255,228,225]', '[255,228,181]', '[255,222,173]', '[0,0,128]', '[253,245,230]', '[128,128,0]', '[107,142,35]', '[255,165,0]', '[255,69,0]', '[218,112,214]', '[238,232,170]', '[152,251,152]', '[175,238,238]', '[219,112,147]', '[255,239,213]', '[255,218,185]', '[205,133,63]', '[255,192,203]', '[221,160,221]', '[176,224,230]', '[128,0,128]', '[255,0,0]', '[188,143,143]', '[65,105,225]', '[139,69,19]', '[250,128,114]', '[244,164,96]', '[46,139,87]', '[255,245,238]', '[160,82,45]', '[192,192,192]', '[135,206,235]', '[106,90,205]', '[112,128,144]', '[255,250,250]', '[0,255,127]', '[70,130,180]', '[210,180,140]', '[0,128,128]', '[216,191,216]', '[255,99,71]', '[64,224,208]', '[238,130,238]', '[245,222,179]', '[255,255,255]', '[245,245,245]', '[255,255,0]', '[154,205,50]'],\
            "html_name":['AliceBlue', 'AntiqueWhite', 'Aqua', 'Aquamarine', 'Azure', 'Beige', 'Bisque', 'Black', 'BlanchedAlmond', 'Blue', 'BlueViolet', 'Brown', 'BurlyWood', 'CadetBlue', 'Chartreuse', 'Chocolate', 'Coral', 'CornflowerBlue', 'Cornsilk', 'Crimson', 'Cyan', 'DarkBlue', 'DarkCyan', 'DarkGoldenrod', 'DarkGray', 'DarkGreen', 'DarkKhaki', 'DarkMagenta', 'DarkOliveGreen', 'DarkOrange', 'DarkOrchid', 'DarkRed', 'DarkSalmon', 'DarkSeaGreen', 'DarkSlateBlue', 'DarkSlateGray', 'DarkTurquoise', 'DarkViolet', 'DeepPink', 'DeepSkyBlue', 'DimGray', 'DodgerBlue', 'FireBrick', 'FloralWhite', 'ForestGreen', 'Fuchsia', 'Gainsboro', 'GhostWhite', 'Gold', 'Goldenrod', 'Gray', 'Green', 'GreenYellow', 'Honeydew', 'HotPink', 'IndianRed', 'Indigo', 'Ivory', 'Khaki', 'Lavender', 'LavenderBlush', 'LawnGreen', 'LemonChiffon', 'LightBlue', 'LightCoral', 'LightCyan', 'LightGoldenrodYellow', 'LightGreen', 'LightGrey', 'LightPink', 'LightSalmon', 'LightSeaGreen', 'LightSkyBlue', 'LightSlateGray', 'LightSteelBlue', 'LightYellow', 'Lime', 'LimeGreen', 'Linen', 'Magenta', 'Maroon', 'MediumAquamarine', 'MediumBlue', 'MediumOrchid', 'MediumPurple', 'MediumSeaGreen', 'MediumSlateBlue', 'MediumSpringGreen', 'MediumTurquoise', 'MediumVioletRed', 'MidnightBlue', 'MintCream', 'MistyRose', 'Moccasin', 'NavajoWhite', 'Navy', 'OldLace', 'Olive', 'OliveDrab', 'Orange', 'OrangeRed', 'Orchid', 'PaleGoldenrod', 'PaleGreen', 'PaleTurquoise', 'PaleVioletRed', 'PapayaWhip', 'PeachPuff', 'Peru', 'Pink', 'Plum', 'PowderBlue', 'Purple', 'Red', 'RosyBrown', 'RoyalBlue', 'SaddleBrown', 'Salmon', 'SandyBrown', 'SeaGreen', 'Seashell', 'Sienna', 'Silver', 'SkyBlue', 'SlateBlue', 'SlateGray', 'Snow', 'SpringGreen', 'SteelBlue', 'Tan', 'Teal', 'Thistle', 'Tomato', 'Turquoise', 'Violet', 'Wheat', 'White', 'WhiteSmoke', 'Yellow', 'YellowGreen'],\
            "hex_string":['#F0F8FF', '#FAEBD7', '#00FFFF', '#7FFFD4', '#F0FFFF', '#F5F5DC', '#FFE4C4', '#000000', '#FFEBCD', '#0000FF', '#8A2BE2', '#A52A2A', '#DEB887', '#5F9EA0', '#7FFF00', '#D2691E', '#FF7F50', '#6495ED', '#FFF8DC', '#DC143C', '#00FFFF', '#00008B', '#008B8B', '#B8860B', '#A9A9A9', '#006400', '#BDB76B', '#8B008B', '#556B2F', '#FF8C00', '#9932CC', '#8B0000', '#E9967A', '#8FBC8F', '#483D8B', '#2F4F4F', '#00CED1', '#9400D3', '#FF1493', '#00BFFF', '#696969', '#1E90FF', '#B22222', '#FFFAF0', '#228B22', '#FF00FF', '#DCDCDC', '#F8F8FF', '#FFD700', '#DAA520', '#808080', '#008000', '#ADFF2F', '#F0FFF0', '#FF69B4', '#CD5C5C', '#4B0082', '#FFFFF0', '#F0E68C', '#E6E6FA', '#FFF0F5', '#7CFC00', '#FFFACD', '#ADD8E6', '#F08080', '#E0FFFF', '#FAFAD2', '#90EE90', '#D3D3D3', '#FFB6C1', '#FFA07A', '#20B2AA', '#87CEFA', '#778899', '#B0C4DE', '#FFFFE0', '#00FF00', '#32CD32', '#FAF0E6', '#FF00FF', '#800000', '#66CDAA', '#0000CD', '#BA55D3', '#9370DB', '#3CB371', '#7B68EE', '#00FA9A', '#48D1CC', '#C71585', '#191970', '#F5FFFA', '#FFE4E1', '#FFE4B5', '#FFDEAD', '#000080', '#FDF5E6', '#808000', '#6B8E23', '#FFA500', '#FF4500', '#DA70D6', '#EEE8AA', '#98FB98', '#AFEEEE', '#DB7093', '#FFEFD5', '#FFDAB9', '#CD853F', '#FFC0CB', '#DDA0DD', '#B0E0E6', '#800080', '#FF0000', '#BC8F8F', '#4169E1', '#8B4513', '#FA8072', '#F4A460', '#2E8B57', '#FFF5EE', '#A0522D', '#C0C0C0', '#87CEEB', '#6A5ACD', '#708090', '#FFFAFA', '#00FF7F', '#4682B4', '#D2B48C', '#008080', '#D8BFD8', '#FF6347', '#40E0D0', '#EE82EE', '#F5DEB3', '#FFFFFF', '#F5F5F5', '#FFFF00', '#9ACD32']}
        df_color = pd.DataFrame(color_data)
        df_color["html_name"] = df_color["html_name"].str.lower()

        # if len(sbmlStr) == 0:
        #   if showDialogues:
        #     wx.MessageBox("Please import an SBML file.", "Message", wx.OK | wx.ICON_INFORMATION)
        # else:
        if len(sbmlStr) != 0:
            net_index = 0
            api.clear_network(net_index)
            comp_id_list = []
            compGlyph_id_list = []
            comp_dimension_list = []
            comp_position_list = []
            spec_id_list = []
            spec_name_list = []
            spec_SBO_list = []
            specGlyph_id_list = []
            spec_specGlyph_id_list = []
            spec_dimension_list = []
            spec_position_list = []
            spec_text_alignment_list = []
            spec_text_position_list = []
            spec_concentration_list = []
            textGlyph_spec_id_list = []
            spec_text_content_list = []

            comp_render = []
            spec_render = []
            rxn_render = []
            text_render = []

            shapeIdx = 0

            
            #set the default values without render info:
            #comp_fill_color = (158, 169, 255, 200)
            #comp_border_color = (0, 29, 255, 255)
            comp_fill_color = (255, 255, 255, 255)
            comp_border_color = (255, 255, 255, 255)
            comp_border_width = 2.0
            spec_fill_color = (255, 204, 153, 200)
            spec_border_color = (255, 108, 9, 255)
            spec_border_width = 2.0
            reaction_line_color = (91, 176, 253, 255)
            reaction_line_width = 3.0
            text_content = ''
            text_line_color = (0, 0, 0, 255)
            text_line_width = 1.
            text_font_size = 12.
            text_font_family = ""
            [text_anchor, text_vanchor] = ['middle', 'middle']
            

            mplugin = None
            try: #possible invalid sbml
                ### from here for layout ###
                document = readSBMLFromString(sbmlStr)
                if document.getNumErrors() != 0:
                    errMsgRead = document.getErrorLog().toString()
                    raise Exception("Errors in SBML Model: ", errMsgRead)
                        
                model_layout = document.getModel()
                try:
                    mplugin = model_layout.getPlugin("layout")
                except:
                    raise Exception("There is no layout.") 
                
                sbml_definitions =[model_layout.getFunctionDefinition(n) for n 
                    in range(model_layout.getNumFunctionDefinitions())]
                function_definitions = [FunctionDefinition(s) for s in sbml_definitions]
                
                # Get the first Layout object via LayoutModelPlugin object.
                #
                # if mplugin is None:
                #     if showDialogues:
                #         wx.MessageBox("There is no layout information, so positions are randomly assigned.", "Message", wx.OK | wx.ICON_INFORMATION)
                # else:
                #def_canvas_width = 10000.
                #def_canvas_height = 6200.
                def_canvas_width = get_theme('real_canvas_width')
                def_canvas_height = get_theme('real_canvas_height')
                #def_comp_width = def_canvas_width - 20.
                #def_comp_height = def_canvas_height - 20.
                def_comp_width = SBMLDiagrams.load(sbmlStr).getNetworkBottomRightCorner().x + 100.
                def_comp_height = SBMLDiagrams.load(sbmlStr).getNetworkBottomRightCorner().y + 100.
                if SBMLDiagrams.load(sbmlStr).getNetworkTopLeftCorner().x < 0:
                    def_comp_width -= SBMLDiagrams.load(sbmlStr).getNetworkTopLeftCorner().x
                if SBMLDiagrams.load(sbmlStr).getNetworkTopLeftCorner().y < 0:
                    def_comp_height -= SBMLDiagrams.load(sbmlStr).getNetworkTopLeftCorner().y
                if mplugin is not None:
                    layout = mplugin.getLayout(0)
                    # if layout is None:
                    #     if showDialogues:
                    #         wx.MessageBox("There is no layout information, so positions are randomly assigned.", "Message", wx.OK | wx.ICON_INFORMATION)
                    # else:
                    try:
                        layout_width = layout.getDimensions().getWidth()
                        layout_height = layout.getDimensions().getHeight()
                    except:
                        layout_width = def_comp_width
                        layout_height = def_comp_height
                    if layout_width >= def_canvas_width or layout_height >= def_canvas_height:
                        if showDialogues:
                            wx.MessageBox("Network layout is beyond the canvas size!.", "Message", wx.OK | wx.ICON_INFORMATION)

                    if layout is not None:
                        numCompGlyphs = layout.getNumCompartmentGlyphs()
                        numSpecGlyphs = layout.getNumSpeciesGlyphs()
                        numReactionGlyphs = layout.getNumReactionGlyphs()
                        numTextGlyphs = layout.getNumTextGlyphs()
                        for i in range(numCompGlyphs):
                            compGlyph = layout.getCompartmentGlyph(i)
                            temp_id = compGlyph.getCompartmentId()
                            comp_id_list.append(temp_id)
                            compGlyph_id = compGlyph.getId()
                            compGlyph_id_list.append(compGlyph_id)
                            boundingbox = compGlyph.getBoundingBox()
                            height = boundingbox.getHeight()
                            width = boundingbox.getWidth()
                            pos_x = boundingbox.getX()
                            pos_y = boundingbox.getY()
                            comp_dimension_list.append([width,height])
                            comp_position_list.append([pos_x,pos_y])
                        if "_compartment_default_" in comp_id_list:
                            numCompGlyphs -= 1
                            idx = comp_id_list.index("_compartment_default_")
                            comp_id_list.remove("_compartment_default_")
                            del compGlyph_id_list[idx]
                            del comp_dimension_list[idx]
                            del comp_position_list[idx]                      


                        reaction_id_list = []
                        reactionGlyph_id_list = []
                        reaction_center_list = []
                        kinetics_list = []
                        #rct_specGlyph_list = []
                        #prd_specGlyph_list = []
                        reaction_center_handle_list = []
                        rct_specGlyph_handle_list = []
                        prd_specGlyph_handle_list = []
                        reaction_mod_list = []
                        reaction_rct_list = []
                        reaction_prd_list = []
                        mod_specGlyph_list = []
                        reaction_type_list = []  

                        for i in range(numReactionGlyphs):
                            reaction_straight_flag = 1
                            reactionGlyph = layout.getReactionGlyph(i)
                            reaction_id = reactionGlyph.getReactionId()
                            reactionGlyph_id = reactionGlyph.getId()
                            curve = reactionGlyph.getCurve()
                            # listOfCurveSegments = curve.getListOfCurveSegments()
                            # for j in range(len(listOfCurveSegments)):
                            #     #center_x = curve.getCurveSegment(j).getStart().x()
                            #     #center_y = curve.getCurveSegment(j).getStart().y()
                            #     center_x = curve.getCurveSegment(j).getStart().getXOffset()
                            #     center_y = curve.getCurveSegment(j).getStart().getYOffset()
                            # for segment in curve.getListOfCurveSegments():
                            #     center_x = segment.getStart().getXOffset()
                            #     center_y = segment.getStart().getYOffset()
                            #     center_pt = [center_x, center_y]
                            #     reaction_center_list.append(center_pt)
                            
                            center_pt = []
                            center_sz = []
                            for segment in curve.getListOfCurveSegments():
                                short_line_start_x = segment.getStart().getXOffset()
                                short_line_start_y = segment.getStart().getYOffset()
                                short_line_end_x   = segment.getEnd().getXOffset()
                                short_line_end_y   = segment.getEnd().getYOffset() 
                                short_line_start = [short_line_start_x, short_line_start_y]
                                short_line_end   = [short_line_end_x, short_line_end_y]
                                if short_line_start == short_line_end: #the centroid is a dot
                                    center_pt = short_line_start
                                else: #the centroid is a short line
                                    center_pt = [.5*(short_line_start_x+short_line_end_x),.5*(short_line_start_y+short_line_end_y)]

                            try:
                                rxn_boundingbox = reactionGlyph.getBoundingBox()
                                width = rxn_boundingbox.getWidth()
                                height = rxn_boundingbox.getHeight()
                                pos_x = rxn_boundingbox.getX()
                                pos_y = rxn_boundingbox.getY()
                                if center_pt == []:
                                    if pos_x == 0 and pos_y == 0 and width == 0 and height == 0: #LinearChain.xml
                                        center_pt = []
                                        #if the boundingbox can not give the info for the center point,
                                        #look for the common point of the start and end points
                                        start_end_pt = []
                                        for j in range(numSpecRefGlyphs):     
                                            specRefGlyph = reactionGlyph.getSpeciesReferenceGlyph(j)   
                                            curve = specRefGlyph.getCurve()                                  
                                            for segment in curve.getListOfCurveSegments():
                                                line_start_x = segment.getStart().getXOffset()
                                                line_start_y = segment.getStart().getYOffset()
                                                line_end_x = segment.getEnd().getXOffset()
                                                line_end_y = segment.getEnd().getYOffset()
                                                line_start_pt =  [line_start_x, line_start_y]
                                                line_end_pt = [line_end_x, line_end_y]
                                                if line_start_pt in start_end_pt:
                                                    center_pt = line_start_pt
                                                if line_end_pt in start_end_pt:
                                                    center_pt = line_end_pt
                                                else:
                                                    start_end_pt.append(line_start_pt)
                                                    start_end_pt.append(line_end_pt)
                                    else:
                                        center_pt = [pos_x+.5*width, pos_y+.5*height]
                                center_sz = [width, height]
                            except:
                                pass
                            
                            reaction_center_list.append(center_pt)
                            #reaction_size_list.append(center_sz)
                            
                            reaction_id = reactionGlyph.getReactionId()
                           
                            reaction_id_list.append(reaction_id)
                            reactionGlyph_id_list.append(reactionGlyph_id)
                            reaction = model_layout.getReaction(reaction_id)
                            try:
                                kinetics = reaction.getKineticLaw().getFormula()
                                if len(function_definitions) > 0:
                                    #kinetics = _expandFormula(kinetics, function_definitions)
                                    kinetics = ""
                            except:
                                kinetics = ""
                            kinetics_list.append(kinetics)

                            temp_mod_list = []
                            for j in range(len(reaction.getListOfModifiers())):
                                modSpecRef = reaction.getModifier(j)
                                temp_mod_list.append(modSpecRef.getSpecies())
                            reaction_mod_list.append(temp_mod_list)

                            temp_rct_list = []
                            for j in range(len(reaction.getListOfReactants())):
                                rctSpecRef = reaction.getReactant(j)
                                temp_rct_list.append(rctSpecRef.getSpecies())
                            reaction_rct_list.append(temp_rct_list)

                            temp_prd_list = []
                            for j in range(len(reaction.getListOfProducts())):
                                prdSpecRef = reaction.getProduct(j)
                                temp_prd_list.append(prdSpecRef.getSpecies())
                            reaction_prd_list.append(temp_prd_list)

                            numSpecRefGlyphs = reactionGlyph.getNumSpeciesReferenceGlyphs()

                            #rct_specGlyph_temp_list = []
                            #prd_specGlyph_temp_list = []
                            rct_specGlyph_handles_temp_list = []
                            prd_specGlyph_handles_temp_list = []  
                            mod_specGlyph_temp_list = []

                            center_handle = [[],[]]

                            for j in range(numSpecRefGlyphs):
                                alignment_name = TextAlignment.CENTER
                                position_name = TextPosition.IN_NODE
                                specRefGlyph = reactionGlyph.getSpeciesReferenceGlyph(j)
                                specRefGlyph_id = specRefGlyph.getId()
                                curve = specRefGlyph.getCurve() 
                                spec_handle = []  
                                modifier_lineend_pos = []
                                spec_lineend_pos = []
                                center_handle_candidate = []
                                spec_handle = []
                                num_curve = curve.getNumCurveSegments()
                                
                                line_start_list = []
                                line_end_list = []                            
                                for segment in curve.getListOfCurveSegments():
                                    line_start_x = segment.getStart().getXOffset()
                                    line_start_y = segment.getStart().getYOffset()
                                    line_end_x = segment.getEnd().getXOffset()
                                    line_end_y = segment.getEnd().getYOffset()
                                    line_start_pt =  [line_start_x, line_start_y]
                                    line_end_pt = [line_end_x, line_end_y]
                                    line_start_list.append(line_start_pt)
                                    line_end_list.append(line_end_pt)
                                try:
                                    line_start_pt =  [line_start_list[0][0], line_start_list[0][1]]
                                    line_end_pt = [line_end_list[num_curve-1][0], line_end_list[num_curve-1][1]]
                                except:
                                    line_start_pt = []
                                    line_end_pt = []


                                try:
                                    dist_start_center = math.sqrt((line_start_pt[0]-center_pt[0])*(line_start_pt[0]-center_pt[0])+(line_start_pt[1]-center_pt[1])*(line_start_pt[1]-center_pt[1]))
                                    dist_end_center = math.sqrt((line_end_pt[0]-center_pt[0])*(line_end_pt[0]-center_pt[0])+(line_end_pt[1]-center_pt[1])*(line_end_pt[1]-center_pt[1]))
                                    #if math.sqrt(line_start_pt, center_pt) <= math.dist(line_end_pt, center_pt):
                                    if dist_start_center <= dist_end_center:
                                        #line starts from center
                                        spec_lineend_pos = line_end_pt
                                        modifier_lineend_pos = line_start_pt
                                        
                                        if num_curve == 1:
                                            try_flag = 0
                                            try: #bezier
                                                center_handle_candidate = [segment.getBasePoint1().getXOffset(), 
                                                                segment.getBasePoint1().getYOffset()]                                
                                                spec_handle = [segment.getBasePoint2().getXOffset(),
                                                            segment.getBasePoint2().getYOffset()]
                                                
                                            except: #straight
                                                spec_handle = [.5*(center_pt[0]+line_end_pt[0]),
                                                .5*(center_pt[1]+line_end_pt[1])]
                                                center_handle_candidate = center_pt
                                                try_flag = 1
                                                #spec_handle = []
                                                #center_handle_candidate = []
                                                #spec_handle = center_pt 
                                            if try_flag == 0:
                                                reaction_straight_flag = 0 

                                        else:
                                            reaction_straight_flag = 0  
                                            try: #bezier
                                                center_handle_candidate = []  
                                                flag_bezier = 0  
                                                for segment in curve.getListOfCurveSegments():
                                                    if segment.getTypeCode() == 102:
                                                        flag_bezier = 1
                                                for segment in curve.getListOfCurveSegments():
                                                    if flag_bezier == 1: 
                                                        #102 CubicBezier #107LineSegment
                                                        if segment.getTypeCode() == 102:
                                                            spec_handle = [segment.getBasePoint1().getXOffset(), 
                                                                        segment.getBasePoint1().getYOffset()]                                
                                                            center_handle_candidate = center_pt
                                                    else:
                                                        spec_handle = [.5*(center_pt[0]+line_start_pt[0]),
                                                        .5*(center_pt[1]+line_start_pt[1])]
                                                        center_handle_candidate = center_pt
                                                        #spec_handle = center_pt
                                            except: #straight
                                                spec_handle = [.5*(center_pt[0]+line_end_pt[0]),
                                                .5*(center_pt[1]+line_end_pt[1])]
                                                center_handle_candidate = center_pt
                                                #spec_handle = center_pt 
                                    else:
                                        #line starts from species
                                        spec_lineend_pos = line_start_pt
                                        modifier_lineend_pos = line_end_pt
                                        
                                        if num_curve == 1:
                                            try_flag = 0
                                            try: #bezier
                                                spec_handle = [segment.getBasePoint1().getXOffset(), 
                                                                    segment.getBasePoint1().getYOffset()]                                
                                                center_handle_candidate = [segment.getBasePoint2().getXOffset(),
                                                                segment.getBasePoint2().getYOffset()]
                                            except: #straight
                                                spec_handle = [.5*(center_pt[0]+line_start_pt[0]),
                                                .5*(center_pt[1]+line_start_pt[1])]
                                                center_handle_candidate = center_pt
                                                #spec_handle = center_pt
                                                try_flag = 1
                                            if try_flag == 0:
                                                reaction_straight_flag = 0 
                                        else:
                                            reaction_straight_flag = 0 
                                            try: #bezier
                                                center_handle_candidate = [] 
                                                flag_bezier = 0  
                                                for segment in curve.getListOfCurveSegments():
                                                    if segment.getTypeCode() == 102:
                                                        flag_bezier = 1
                                                for segment in curve.getListOfCurveSegments():
                                                    if flag_bezier == 1: 
                                                        #102 CubicBezier #107LineSegment
                                                        if segment.getTypeCode() == 102:
                                                            spec_handle = [segment.getBasePoint1().getXOffset(), 
                                                                        segment.getBasePoint1().getYOffset()]                                
                                                            center_handle_candidate = center_pt
                                                    else:
                                                        spec_handle = [.5*(center_pt[0]+line_start_pt[0]),
                                                        .5*(center_pt[1]+line_start_pt[1])]
                                                        center_handle_candidate = center_pt
                                                        #spec_handle = center_pt
                                            except: #straight
                                                spec_handle = [.5*(center_pt[0]+line_start_pt[0]),
                                                .5*(center_pt[1]+line_start_pt[1])]
                                                center_handle_candidate = center_pt
                                                #spec_handle = center_pt

                                except:
                                    reaction_straight_flag = 0 
                                    center_handle_candidate = []
                                    spec_handle = []

                                role = specRefGlyph.getRoleString()
                                specGlyph_id = specRefGlyph.getSpeciesGlyphId()
                                specGlyph = layout.getSpeciesGlyph(specGlyph_id)
                                
                                # for k in range(numSpecGlyphs):
                                #     textGlyph_temp = layout.getTextGlyph(k)
                                #     temp_specGlyph_id = textGlyph_temp.getOriginOfTextId()
                                #     if temp_specGlyph_id == specGlyph_id:
                                #         textGlyph = textGlyph_temp
                                for k in range(numTextGlyphs):
                                    textGlyph_temp = layout.getTextGlyph(k)
                                    # if textGlyph_temp.isSetOriginOfTextId():
                                    #     temp_specGlyph_id = textGlyph_temp.getOriginOfTextId()
                                    if textGlyph_temp.isSetGraphicalObjectId():
                                        temp_specGlyph_id = textGlyph_temp.getGraphicalObjectId()
                                    else:
                                        temp_specGlyph_id = ''
                                    if temp_specGlyph_id == specGlyph_id:
                                        textGlyph = textGlyph_temp
                                        text_content = textGlyph.getText()
                                        temp_id = textGlyph.getId()
                                        textGlyph_spec_id_list.append([specGlyph_id, temp_id])


                                spec_id = specGlyph.getSpeciesId()
                                spec = model_layout.getSpecies(spec_id)
                                spec_name = spec.getName()
                                spec_SBO = spec.getSBOTermID()
                                #print(spec_SBO)
                                
                                try:
                                    concentration = spec.getInitialConcentration()
                                    if math.nan(concentration):
                                        concentration = 1
                                except:
                                    concentration = 1.
                                spec_boundingbox = specGlyph.getBoundingBox()
                                height = spec_boundingbox.getHeight()
                                width = spec_boundingbox.getWidth()
                                pos_x = spec_boundingbox.getX()
                                pos_y = spec_boundingbox.getY()

                                try:
                                    text_boundingbox = textGlyph.getBoundingBox()
                                    text_pos_x = text_boundingbox.getX()
                                    text_pos_y = text_boundingbox.getY()
                                    # if text_pos_x < pos_x:
                                    #     alignment_name = TextAlignment.LEFT
                                    # if text_pos_x > pos_x:
                                    #     alignment_name = TextAlignment.RIGHT  
                                    # if text_pos_y < pos_y:
                                    #     position_name = TextPosition.ABOVE
                                    # if text_pos_y > pos_y:
                                    #     position_name = TextPosition.BELOW
                                    # if text_pos_y == pos_y and text_pos_x != pos_x:
                                    #     position_name = TextPosition.NEXT_TO 
                                    if text_pos_x < pos_x - 0.5*width:
                                        alignment_name = TextAlignment.LEFT
                                        if text_pos_y >= pos_y - 0.5*height or text_pos_y <= pos_y + 0.5*height:
                                            position_name = TextPosition.NEXT_TO 
                                    if text_pos_x > pos_x + 0.5*width:
                                        alignment_name = TextAlignment.RIGHT
                                        if text_pos_y >= pos_y - 0.5*height or text_pos_y <= pos_y + 0.5*height:
                                            position_name = TextPosition.NEXT_TO   
                                    if text_pos_y < pos_y - 0.5*height:
                                        position_name = TextPosition.ABOVE
                                    if text_pos_y > pos_y + 0.5*height:
                                        position_name = TextPosition.BELOW
                                   
                                except:
                                    pass  
                    

                                if specGlyph_id not in specGlyph_id_list:
                                    spec_id_list.append(spec_id)
                                    spec_name_list.append(spec_name)
                                    spec_SBO_list.append(spec_SBO)
                                    specGlyph_id_list.append(specGlyph_id)
                                    spec_specGlyph_id_list.append([spec_id,specGlyph_id])
                                    spec_dimension_list.append([width,height])
                                    spec_position_list.append([pos_x,pos_y])
                                    if text_content == '':
                                        if spec_name != '':
                                            text_content = spec_name
                                        else:
                                            text_content = spec_id
                                    spec_text_content_list.append(text_content)
                                    spec_text_alignment_list.append(alignment_name)
                                    spec_text_position_list.append(position_name)
                                    spec_concentration_list.append(concentration)

                              
                                if role == "substrate" or role == "sidesubstrate": #it is a rct
                                    #the center handle is supposed to be from the reactant
                                    if center_handle[0] == []:
                                        center_handle[0] = center_handle_candidate
                                    #rct_specGlyph_temp_list.append(specGlyph_id)
                                    rct_specGlyph_handles_temp_list.append([specGlyph_id,spec_handle,specRefGlyph_id,spec_lineend_pos])
                                elif role == "product" or role == "sideproduct": #it is a prd
                                    #prd_specGlyph_temp_list.append(specGlyph_id)
                                    if center_handle[1] == []:
                                        center_handle[1] = center_handle_candidate
                                    prd_specGlyph_handles_temp_list.append([specGlyph_id,spec_handle,specRefGlyph_id,spec_lineend_pos])
                                elif role == "modifier" or role == 'activator' or role == "inhibitor": #it is a modifier
                                    mod_specGlyph_temp_list.append([specGlyph_id, role])
                            #rct_specGlyph_list.append(rct_specGlyph_temp_list)
                            #prd_specGlyph_list.append(prd_specGlyph_temp_list)
                            try:
                                if center_handle[0] != []:
                                    reaction_center_handle_list.append(center_handle[0])
                                else:
                                    reaction_center_handle_list.append(center_handle[1])
                            except:
                                #raise Exception("Can not find center handle information to process.")
                                reaction_center_handle_list.append([])
                            rct_specGlyph_handle_list.append(rct_specGlyph_handles_temp_list)
                            prd_specGlyph_handle_list.append(prd_specGlyph_handles_temp_list)    
                            mod_specGlyph_list.append(mod_specGlyph_temp_list)
                            if reaction_straight_flag == 1:
                                reaction_type_list.append(False)#straight line
                            else:
                                reaction_type_list.append(True)#bezier curve

                        #orphan nodes
                        for i in range(numSpecGlyphs):
                            specGlyph = layout.getSpeciesGlyph(i)
                            specGlyph_id = specGlyph.getId()
                            if specGlyph_id not in specGlyph_id_list:
                                specGlyph_id_list.append(specGlyph_id)
                                spec_id = specGlyph.getSpeciesId()
                                spec = model_layout.getSpecies(spec_id)
                                spec_name = spec.getName()
                                spec_SBO = spec.getSBOTermID()
                                spec_id_list.append(spec_id)
                                spec_name_list.append(spec_name)
                                spec_SBO_list.append(spec_SBO)
                                spec_specGlyph_id_list.append([spec_id,specGlyph_id])
                                boundingbox = specGlyph.getBoundingBox()
                                height = boundingbox.getHeight()
                                width = boundingbox.getWidth()
                                pos_x = boundingbox.getX()
                                pos_y = boundingbox.getY()
                                spec_dimension_list.append([width,height])
                                spec_position_list.append([pos_x,pos_y])
                                try:
                                    concentration = spec.getInitialConcentration()
                                    if math.nan(concentration):
                                        concentration = 1
                                except:
                                    concentration = 1.
                                spec_concentration_list.append(concentration)
                                alignment_name = TextAlignment.CENTER
                                position_name = TextPosition.IN_NODE
                                for k in range(numTextGlyphs):
                                    textGlyph_temp = layout.getTextGlyph(k)
                                    if textGlyph_temp != None:
                                        #temp_specGlyph_id = textGlyph_temp.getOriginOfTextId()
                                        if textGlyph_temp.isSetGraphicalObjectId():
                                            temp_specGlyph_id = textGlyph_temp.getGraphicalObjectId()
                                        else:
                                            temp_specGlyph_id = ''
                                        if temp_specGlyph_id == specGlyph_id:
                                            textGlyph = textGlyph_temp
                                            text_content = textGlyph.getText()
                                            temp_id = textGlyph.getId()
                                            textGlyph_spec_id_list.append([specGlyph_id, temp_id])

                                try:
                                    text_boundingbox = textGlyph.getBoundingBox()
                                    text_pos_x = text_boundingbox.getX()
                                    text_pos_y = text_boundingbox.getY()
                                    if text_pos_x < pos_x - 0.5*width:
                                        alignment_name = TextAlignment.LEFT
                                        if text_pos_y >= pos_y - 0.5*height or text_pos_y <= pos_y + 0.5*height:
                                            position_name = TextPosition.NEXT_TO 
                                    if text_pos_x > pos_x + 0.5*width:
                                        alignment_name = TextAlignment.RIGHT
                                        if text_pos_y >= pos_y - 0.5*height or text_pos_y <= pos_y + 0.5*height:
                                            position_name = TextPosition.NEXT_TO   
                                    if text_pos_y < pos_y - 0.5*height:
                                        position_name = TextPosition.ABOVE
                                    if text_pos_y > pos_y + 0.5*height:
                                        position_name = TextPosition.BELOW
                                except:
                                    pass
                                spec_text_alignment_list.append(alignment_name)
                                spec_text_position_list.append(position_name)
                                if text_content == '':
                                    text_content = spec_id
                                spec_text_content_list.append(text_content)
                        
                        #print(reaction_mod_list)
                        #print(mod_specGlyph_list)
                        #print(spec_specGlyph_id_list)
                        #local render
                        rPlugin = layout.getPlugin("render")
                        if (rPlugin != None and rPlugin.getNumLocalRenderInformationObjects() > 0):
                        #if rPlugin != None:
                            #wx.MessageBox("The diversity of each graphical object is not shown.", "Message", wx.OK | wx.ICON_INFORMATION)
                            info = rPlugin.getRenderInformation(0)
                            color_list = []
                            # comp_render = []
                            # spec_render = []
                            # rxn_render = []
                            # text_render = []
                            # for j in range(0, info.getNumLineEndings()):
                            #     LineEnding = info.getLineEndings(j)

                            for  j in range (0, info.getNumColorDefinitions()):
                                color = info.getColorDefinition(j)
                                color_list.append([color.getId(),color.createValueString()])

                            for j in range (0, info.getNumStyles()):
                                style = info.getStyle(j)
                                group = style.getGroup()
                                # for element in group.getListOfElements(): 
                                #     print(element.getElementName(), element.getStroke())
                                typeList = style.createTypeString()
                                idList = style.createIdString()
                                roleList = style.createRoleString()

                                if typeList == '': 
                                    #if the typeList is not defined, self define it based on idList
                                    #which is the layout id instead of id
                                    if idList in compGlyph_id_list:
                                        typeList = 'COMPARTMENTGLYPH'
                                    elif idList in specGlyph_id_list:
                                        typeList = 'SPECIESGLYPH'
                                    elif idList in reactionGlyph_id_list:
                                        typeList = 'REACTIONGLYPH'
                                    elif any(idList in sublist for sublist in textGlyph_spec_id_list):
                                        typeList = 'TEXTGLYPH'
                                    # else:
                                    #     print(idList)
                                    # elif idList == "":
                                    #     print(roleList)

                                if 'COMPARTMENTGLYPH' in typeList:
                                    render_comp_id = idList
                                    for k in range(len(compGlyph_id_list)):    
                                        if compGlyph_id_list[k] == idList:
                                            render_comp_id = comp_id_list[k]  
                                    if idList == 'CompG__compartment_default_':
                                        render_comp_id = '_compartment_default_'                            

                                    fill_color = group.getFill()
                                    if fill_color.lower() in df_color.values:
                                        index = df_color.index[df_color["html_name"] == fill_color.lower()].tolist()[0] #row index 
                                        rgb_pre = df_color.iloc[index]["decimal_rgb"]
                                        rgb_pre = rgb_pre[1:-1].split(",")
                                        rgb = [int(x) for x in rgb_pre]
                                        comp_fill_color = rgb                 
                                    else:
                                        try:
                                            comp_fill_color = hex_to_rgb(fill_color)                          
                                        except:
                                            for k in range(len(color_list)):
                                                if color_list[k][0] == fill_color:
                                                    comp_fill_color = hex_to_rgb(color_list[k][1])

                                    border_color = group.getStroke()
                                    if border_color.lower() in df_color.values:
                                        index = df_color.index[df_color["html_name"] == border_color.lower()].tolist()[0] #row index 
                                        rgb_pre = df_color.iloc[index]["decimal_rgb"]
                                        rgb_pre = rgb_pre[1:-1].split(",")
                                        rgb = [int(x) for x in rgb_pre]
                                        comp_border_color = rgb 
                                    else:
                                        try:
                                            comp_border_color = hex_to_rgb(border_color)
                                        except:
                                            for k in range(len(color_list)):
                                                if color_list[k][0] == border_color:
                                                    comp_border_color = hex_to_rgb(color_list[k][1])
                
                                    comp_border_width = group.getStrokeWidth()

                                    shape_type = ""
                                    #print(group.getNumElements())# There is only one element
                                    #for element in group.getListOfElements():
                                    element = group.getElement(0)
                                    shape_name = ""
                                    shapeInfo = []
                                    if element != None:
                                        shape_type = element.getElementName()
                                        if shape_type == "rectangle":
                                            shape_name = "rectangle"
                                            radius_x = element.getRX().getRelativeValue()
                                            radius_y = element.getRY().getRelativeValue()
                                            shapeInfo.append([radius_x, radius_y])
                                    comp_render.append([render_comp_id,comp_fill_color,comp_border_color,comp_border_width, 
                                    shape_name, shape_type, shapeInfo])
                                elif 'SPECIESGLYPH' in typeList:
                                    render_spec_id = idList
                                    for k in range(len(spec_specGlyph_id_list)):    
                                        if spec_specGlyph_id_list[k][1] == idList:
                                            render_spec_id = spec_specGlyph_id_list[k][0] 
                                            spec_dimension = spec_dimension_list[k]

                                    fill_color = group.getFill()
                                    if fill_color.lower() in df_color.values:
                                        index = df_color.index[df_color["html_name"] == fill_color.lower()].tolist()[0] #row index 
                                        rgb_pre = df_color.iloc[index]["decimal_rgb"]
                                        rgb_pre = rgb_pre[1:-1].split(",")
                                        rgb = [int(x) for x in rgb_pre]
                                        spec_fill_color = rgb  
                                    else:
                                        try:#some spec fill color is defined as hex string directly
                                            spec_fill_color = hex_to_rgb(fill_color)
                                        except:
                                            for k in range(len(color_list)):
                                                if color_list[k][0] == fill_color:
                                                    spec_fill_color = hex_to_rgb(color_list[k][1])

                                    border_color = group.getStroke()
                                    if border_color.lower() in df_color.values:
                                        index = df_color.index[df_color["html_name"] == border_color.lower()].tolist()[0] #row index 
                                        rgb_pre = df_color.iloc[index]["decimal_rgb"]
                                        rgb_pre = rgb_pre[1:-1].split(",")
                                        rgb = [int(x) for x in rgb_pre]
                                        spec_border_color = rgb 
                                    else:
                                        try:
                                            spec_border_color = hex_to_rgb(border_color)
                                        except:
                                            for k in range(len(color_list)):
                                                if color_list[k][0] == border_color:
                                                    spec_border_color = hex_to_rgb(color_list[k][1])
                                    if len(spec_border_color) == 3:
                                        spec_border_color.append(255)
                                    spec_dash = []
                                    if group.isSetDashArray():
                                        spec_num_dash = group.getNumDashes()
                                        for num in range(spec_num_dash):
                                            spec_dash.append(group.getDashByIndex(num))
                                        
          
                                    spec_border_width = group.getStrokeWidth()
                                    name_list = []
                                    for element in group.getListOfElements():
                                        name = element.getElementName()
                                        name_list.append(name)
                                        try:
                                            NumRenderpoints = element.getListOfElements().getNumRenderPoints()
                                        except:
                                            NumRenderpoints = 0
                             
                                    if name == "ellipse": #circel and text-outside
                                        shapeIdx = 1
                                    elif name == "polygon" and NumRenderpoints == 6:
                                        shapeIdx = 2
                                    elif name == "polygon" and NumRenderpoints == 2:
                                        shapeIdx = 3
                                    elif name == "polygon" and NumRenderpoints == 3:
                                        shapeIdx = 4
                                    elif name == "rectangle" and spec_fill_color == '#ffffffff' and spec_border_color == '#ffffffff':
                                        shapeIdx = 5
                                    #elif name == "ellipse" and flag_text_out == 1:
                                    #    shapeIdx = 6
                                    else: # name == "rectangle"/demo combo/others as default (rectangle)
                                        shapeIdx = 0
                       
                                    spec_render.append([render_spec_id,spec_fill_color,spec_border_color,spec_border_width,shapeIdx])

                                elif 'REACTIONGLYPH' in typeList:
                                    # for k in range(len(color_list)):
                                    #     if color_list[k][0] == group.getStroke():
                                    #         reaction_line_color = hex_to_rgb(color_list[k][1])
                                    # reaction_line_width = group.getStrokeWidth()

                                    #change layout id to id for later to build the list of render
                                    render_rxn_id = idList
                                    for k in range(len(reactionGlyph_id_list)):    
                                        if reactionGlyph_id_list[k] == idList:
                                            render_rxn_id = reaction_id_list[k] 
                                    if group.isSetEndHead():
                                        temp_id = group.getEndHead() 
                                    reaction_dash = []
                                    if group.isSetDashArray():
                                        reaction_num_dash = group.getNumDashes()
                                        for num in range(reaction_num_dash):
                                            reaction_dash.append(group.getDashByIndex(num))

                                    fill_color = group.getFill()
                                    if fill_color.lower() in df_color.values:
                                        index = df_color.index[df_color["html_name"] == fill_color.lower()].tolist()[0] #row index 
                                        rgb_pre = df_color.iloc[index]["decimal_rgb"]
                                        rgb_pre = rgb_pre[1:-1].split(",")
                                        rgb = [int(x) for x in rgb_pre]
                                        reaction_line_fill = rgb 
                                    try:
                                        reaction_line_fill = hex_to_rgb(fill_color)
                                    except:
                                        for k in range(len(color_list)):
                                            if color_list[k][0] == fill_color:
                                                reaction_line_fill = hex_to_rgb(color_list[k][1])

                                    stroke_color = group.getStroke()
                                    if stroke_color.lower() in df_color.values:
                                        index = df_color.index[df_color["html_name"] == stroke_color.lower()].tolist()[0] #row index 
                                        rgb_pre = df_color.iloc[index]["decimal_rgb"]
                                        rgb_pre = rgb_pre[1:-1].split(",")
                                        rgb = [int(x) for x in rgb_pre]
                                        reaction_line_color = rgb 
                                    else:
                                        try:
                                            reaction_line_color = hex_to_rgb(stroke_color)
                                        except:
                                            for k in range(len(color_list)):
                                                if color_list[k][0] == stroke_color:
                                                    reaction_line_color = hex_to_rgb(color_list[k][1])
                                    
                                    reaction_line_width = group.getStrokeWidth()
                                    rxn_render.append([render_rxn_id, reaction_line_color,reaction_line_width])

                                elif 'TEXTGLYPH' in typeList:
                                    render_text_id = idList
                                    for k in range(len(textGlyph_spec_id_list)):    
                                        if textGlyph_spec_id_list[k][1] == idList:
                                            render_text_id = textGlyph_spec_id_list[k][0]
     
                                    text_color = group.getStroke()
                                    if text_color.lower() in df_color.values:
                                        index = df_color.index[df_color["html_name"] == text_color.lower()].tolist()[0] #row index 
                                        rgb_pre = df_color.iloc[index]["decimal_rgb"]
                                        rgb_pre = rgb_pre[1:-1].split(",")
                                        rgb = [int(x) for x in rgb_pre]
                                        text_line_color = rgb   
                                    else:  
                                        try:
                                            text_line_color = hex_to_rgb(text_color)
                                        except:
                                            for k in range(len(color_list)):
                                                if color_list[k][0] == text_color:
                                                    text_line_color = hex_to_rgb(color_list[k][1])

                                    
                                    text_line_width = group.getStrokeWidth()
                                    if group.isSetTextAnchor():
                                        text_anchor = group.getTextAnchorAsString()
                                    if group.isSetVTextAnchor():
                                        text_vanchor = group.getVTextAnchorAsString()
                                    if math.isnan(text_line_width):
                                        text_line_width = 1.
                                    text_font_size = float(group.getFontSize().getCoordinate())
                                    if math.isnan(text_font_size):
                                        text_font_size = 12.
                                    text_font_family = group.getFontFamily()

                                    text_render.append([render_text_id,text_line_color,text_line_width,
                                    text_font_size, [text_anchor, text_vanchor], idList, text_font_family])
                                    #print(text_render)
                    #print(spec_render)
                    #global render 
                    try: 
                        grPlugin = mplugin.getListOfLayouts().getPlugin("render")
                    except:
                        pass

                    if (grPlugin != None and grPlugin.getNumGlobalRenderInformationObjects() > 0):
                        info = grPlugin.getRenderInformation(0)
                        color_list = []
                      

                        for  j in range(0, info.getNumColorDefinitions()):
                            color = info.getColorDefinition(j)
                            color_list.append([color.getId(),color.createValueString()])

    
                        for j in range (0, info.getNumStyles()):
                            style = info.getStyle(j)
                            group = style.getGroup()
                            typeList = style.createTypeString()
                            roleList = style.createRoleString()
                            idList = ""

                            if roleList == "modifier" or roleList == "product": 
                                typeList = 'SPECIESREFERENCEGLYPH'

                            if 'COMPARTMENTGLYPH' in typeList:
                                render_comp_id = idList

                                fill_color = group.getFill()
                                if fill_color.lower() in df_color.values:
                                    index = df_color.index[df_color["html_name"] == fill_color.lower()].tolist()[0] #row index 
                                    rgb_pre = df_color.iloc[index]["decimal_rgb"]
                                    rgb_pre = rgb_pre[1:-1].split(",")
                                    rgb = [int(x) for x in rgb_pre]
                                    comp_fill_color = rgb                 
                                else:
                                    try:
                                        comp_fill_color = hex_to_rgb(fill_color)                          
                                    except:
                                        for k in range(len(color_list)):
                                            if color_list[k][0] == fill_color:
                                                comp_fill_color = hex_to_rgb(color_list[k][1])

                                border_color = group.getStroke()
                                if border_color.lower() in df_color.values:
                                    index = df_color.index[df_color["html_name"] == border_color.lower()].tolist()[0] #row index 
                                    rgb_pre = df_color.iloc[index]["decimal_rgb"]
                                    rgb_pre = rgb_pre[1:-1].split(",")
                                    rgb = [int(x) for x in rgb_pre]
                                    comp_border_color = rgb 
                                else:
                                    try:
                                        comp_border_color = hex_to_rgb(border_color)
                                    except:
                                        for k in range(len(color_list)):
                                            if color_list[k][0] == border_color:
                                                comp_border_color = hex_to_rgb(color_list[k][1])
            
                                comp_border_width = group.getStrokeWidth()

                                shape_type = ""
                                #print(group.getNumElements())# There is only one element
                                #for element in group.getListOfElements():
                                element = group.getElement(0)
                                shape_name = ""
                                shapeInfo = []
                                if element != None:
                                    shape_type = element.getElementName()
                                    if shape_type == "rectangle":
                                        shape_name = "rectangle"
                                        radius_x = element.getRX().getRelativeValue()
                                        radius_y = element.getRY().getRelativeValue()
                                        shapeInfo.append([radius_x, radius_y])
                                comp_render.append([render_comp_id,comp_fill_color,comp_border_color,comp_border_width, 
                                shape_name, shape_type, shapeInfo])
                            elif 'SPECIESGLYPH' in typeList:
                                render_spec_id = idList
              
                                fill_color = group.getFill()
                                if fill_color.lower() in df_color.values:
                                    index = df_color.index[df_color["html_name"] == fill_color.lower()].tolist()[0] #row index 
                                    rgb_pre = df_color.iloc[index]["decimal_rgb"]
                                    rgb_pre = rgb_pre[1:-1].split(",")
                                    rgb = [int(x) for x in rgb_pre]
                                    spec_fill_color = rgb  
                                else:
                                    try:#some spec fill color is defined as hex string directly
                                        spec_fill_color = hex_to_rgb(fill_color)
                                    except:
                                        for k in range(len(color_list)):
                                            if color_list[k][0] == fill_color:
                                                spec_fill_color = hex_to_rgb(color_list[k][1])

                                border_color = group.getStroke()
                                if border_color.lower() in df_color.values:
                                    index = df_color.index[df_color["html_name"] == border_color.lower()].tolist()[0] #row index 
                                    rgb_pre = df_color.iloc[index]["decimal_rgb"]
                                    rgb_pre = rgb_pre[1:-1].split(",")
                                    rgb = [int(x) for x in rgb_pre]
                                    spec_border_color = rgb 
                                else:
                                    try:
                                        spec_border_color = hex_to_rgb(border_color)
                                    except:
                                        for k in range(len(color_list)):
                                            if color_list[k][0] == border_color:
                                                spec_border_color = hex_to_rgb(color_list[k][1])
                                if len(spec_border_color) == 3:
                                    spec_border_color.append(255)
                                spec_dash = []
                                if group.isSetDashArray():
                                    spec_num_dash = group.getNumDashes()
                                    for num in range(spec_num_dash):
                                        spec_dash.append(group.getDashByIndex(num))
                                    
        
                                spec_border_width = group.getStrokeWidth()
                                name_list = []
                                for element in group.getListOfElements():
                                    name = element.getElementName()
                                    name_list.append(name)
                                    try:
                                        NumRenderpoints = element.getListOfElements().getNumRenderPoints()
                                    except:
                                        NumRenderpoints = 0
                                if name == "ellipse": #circel and text-outside
                                    shapeIdx = 1
                                elif name == "polygon" and NumRenderpoints == 6:
                                    shapeIdx = 2
                                elif name == "polygon" and NumRenderpoints == 2:
                                    shapeIdx = 3
                                elif name == "polygon" and NumRenderpoints == 3:
                                    shapeIdx = 4
                                elif name == "rectangle" and spec_fill_color == '#ffffffff' and spec_border_color == '#ffffffff':
                                    shapeIdx = 5
                                #elif name == "ellipse" and flag_text_out == 1:
                                #    shapeIdx = 6
                                else: # name == "rectangle"/demo combo/others as default (rectangle)
                                    shapeIdx = 0
                                spec_render.append([render_spec_id,spec_fill_color,spec_border_color,spec_border_width,shapeIdx])

                            elif 'REACTIONGLYPH' in typeList:
                                # for k in range(len(color_list)):
                                #     if color_list[k][0] == group.getStroke():
                                #         reaction_line_color = hex_to_rgb(color_list[k][1])
                                # reaction_line_width = group.getStrokeWidth()

                                #change layout id to id for later to build the list of render
                                render_rxn_id = idList
                             
                                reaction_dash = []
                                if group.isSetDashArray():
                                    reaction_num_dash = group.getNumDashes()
                                    for num in range(reaction_num_dash):
                                        reaction_dash.append(group.getDashByIndex(num))

                                fill_color = group.getFill()
                                if fill_color.lower() in df_color.values:
                                    index = df_color.index[df_color["html_name"] == fill_color.lower()].tolist()[0] #row index 
                                    rgb_pre = df_color.iloc[index]["decimal_rgb"]
                                    rgb_pre = rgb_pre[1:-1].split(",")
                                    rgb = [int(x) for x in rgb_pre]
                                    reaction_line_fill = rgb 
                                try:
                                    reaction_line_fill = hex_to_rgb(fill_color)
                                except:
                                    for k in range(len(color_list)):
                                        if color_list[k][0] == fill_color:
                                            reaction_line_fill = hex_to_rgb(color_list[k][1])

                                stroke_color = group.getStroke()
                                if stroke_color.lower() in df_color.values:
                                    index = df_color.index[df_color["html_name"] == stroke_color.lower()].tolist()[0] #row index 
                                    rgb_pre = df_color.iloc[index]["decimal_rgb"]
                                    rgb_pre = rgb_pre[1:-1].split(",")
                                    rgb = [int(x) for x in rgb_pre]
                                    reaction_line_color = rgb 
                                else:
                                    try:
                                        reaction_line_color = hex_to_rgb(stroke_color)
                                    except:
                                        for k in range(len(color_list)):
                                            if color_list[k][0] == stroke_color:
                                                reaction_line_color = hex_to_rgb(color_list[k][1])
                                
                                reaction_line_width = group.getStrokeWidth()
                                rxn_render.append([render_rxn_id, reaction_line_color,reaction_line_width])

                            elif 'TEXTGLYPH' in typeList:
                                render_text_id = idList

                                text_color = group.getStroke()
                                if text_color.lower() in df_color.values:
                                    index = df_color.index[df_color["html_name"] == text_color.lower()].tolist()[0] #row index 
                                    rgb_pre = df_color.iloc[index]["decimal_rgb"]
                                    rgb_pre = rgb_pre[1:-1].split(",")
                                    rgb = [int(x) for x in rgb_pre]
                                    text_line_color = rgb   
                                else:  
                                    try:
                                        text_line_color = hex_to_rgb(text_color)
                                    except:
                                        for k in range(len(color_list)):
                                            if color_list[k][0] == text_color:
                                                text_line_color = hex_to_rgb(color_list[k][1])

                                
                                text_line_width = group.getStrokeWidth()
                                if group.isSetTextAnchor():
                                    text_anchor = group.getTextAnchorAsString()
                                if group.isSetVTextAnchor():
                                    text_vanchor = group.getVTextAnchorAsString()
                                if math.isnan(text_line_width):
                                    text_line_width = 1.
                                text_font_size = float(group.getFontSize().getCoordinate())
                                if math.isnan(text_font_size):
                                    text_font_size = 12.
                                text_font_family = group.getFontFamily()

                                text_render.append([render_text_id,text_line_color,text_line_width,
                                text_font_size, [text_anchor, text_vanchor], idList, text_font_family])
                                #print(text_render)
                                
                model = simplesbml.loadSBMLStr(sbmlStr)
                
                numFloatingNodes  = model.getNumFloatingSpecies()
                FloatingNodes_ids = model.getListOfFloatingSpecies()
                numBoundaryNodes  = model.getNumBoundarySpecies()
                BoundaryNodes_ids = model.getListOfBoundarySpecies()
                numRxns   = model.getNumReactions()
                Rxns_ids  = model.getListOfReactionIds()
                numComps  = model.getNumCompartments()
                Comps_ids = model.getListOfCompartmentIds()
                if "_compartment_default_" in Comps_ids:
                    numComps -= 1
                    Comps_ids.remove("_compartment_default_")
                numNodes = model.getNumSpecies()
                Nodes_ids = model.getListOfAllSpecies()

                parameter_list = model.getListOfParameterIds()

                for p in parameter_list:
                    if model.isParameterValueSet(p): 
                    #if there is only parameter id without parameter value, it won't be considered 
                        api.set_parameter_value(net_index, p, model.getParameterValue(p))

                comp_node_list = [0]*numComps #Note: numComps is different from numCompGlyphs
                for i in range(numComps):
                    comp_node_list[i] = []

            
                #if there is layout info:
                if len(spec_id_list) != 0:
                    comp_specs_in_list = []
                    for i in range(numComps):
                        comp_node_list[i] = []
                    for i in range(numComps):#only consider the compartment with species in
                        for j in range(numFloatingNodes):
                            comp_id = model.getCompartmentIdSpeciesIsIn(FloatingNodes_ids[j])
                            if comp_id not in comp_specs_in_list:
                                comp_specs_in_list.append(comp_id)
                        for j in range(numBoundaryNodes):
                            comp_id = model.getCompartmentIdSpeciesIsIn(BoundaryNodes_ids[j])
                            if comp_id not in comp_specs_in_list:
                                comp_specs_in_list.append(comp_id)
                    #cross check negative positions of compartments and species
                    TopLeft = [0., 0.] # for negative positions 
                    shift = [0., 0.] # for positions beyond the canvas
                    for i in range(numComps):
                        temp_id = Comps_ids[i]
                        if temp_id != "_compartment_default_" and comp_id_list != 0 and (temp_id in comp_specs_in_list):
                            position = [10., 10.]
                            for j in range(numCompGlyphs):
                                if comp_id_list[j] == temp_id:
                                    position = comp_position_list[j]
                            for j in range(len(comp_render)):
                                if temp_id == comp_render[j][0]:
                                    comp_fill_color = comp_render[j][1]
                                    comp_border_color = comp_render[j][2]
                            if len(comp_render) == 1:
                                if comp_render[0][0] == '': #global render
                                    comp_fill_color = comp_render[0][1]
                                    comp_border_color = comp_render[0][2]
                            if comp_fill_color != (255, 255, 255, 0) or comp_border_color != (255, 255, 255, 0):
                                if TopLeft[0] > position[0] or TopLeft[1] > position[1]:
                                    TopLeft = position

                    numSpec_in_reaction = len(spec_specGlyph_id_list) 
                    for i in range (numSpec_in_reaction):
                        temp_id = spec_specGlyph_id_list[i][0]
                        position = spec_position_list[i]
                        if TopLeft[0] > position[0] or TopLeft[1] > position[1]:
                            TopLeft = position

                    for i in range(numComps):
                        temp_id = Comps_ids[i]
                        
                        vol= model.getCompartmentVolume(i)
                        if math.isnan(vol):
                            vol = 1.
                        if temp_id == "_compartment_default_":
                            pass
                            # if len(comp_id_list) != 0:
                            #     dimension = [def_comp_width, def_comp_height]
                            #     position = [10, 10]                  
                            #     for j in range(numCompGlyphs):
                            #         if comp_id_list[j] == temp_id:
                            #             dimension = comp_dimension_list[j]
                            #             position = comp_position_list[j]
                            #     api.add_compartment(net_index, id=temp_id, volume = vol,
                            #     size=Vec2(dimension[0],dimension[1]), position=Vec2(position[0],position[1]),
                            #     fill_color = api.Color(255, 255, 255, 0), #the last digit for transparent
                            #     border_color = api.Color(255, 255, 255, 0),
                            #     border_width = comp_border_width)  
                            # else:
                            #     api.add_compartment(net_index, id=temp_id, volume = vol,
                            #     size=Vec2(def_comp_width,def_comp_height), position=Vec2(10,10),
                            #     fill_color = api.Color(255, 255, 255, 0), #the last digit for transparent
                            #     border_color = api.Color(255, 255, 255, 0),
                            #     border_width = comp_border_width)
                        else:
                            if len(comp_id_list) != 0:
                            #if mplugin is not None:                    
                                for j in range(numCompGlyphs):
                                    if comp_id_list[j] == temp_id:
                                        dimension = comp_dimension_list[j]
                                        position = comp_position_list[j]
                                for j in range(len(comp_render)):
                                    if temp_id == comp_render[j][0]:
                                        comp_fill_color = comp_render[j][1]
                                        comp_border_color = comp_render[j][2]
                                        comp_border_width = comp_render[j][3]
                                if len(comp_render) == 1:
                                    if comp_render[0][0] == '': #global render
                                        comp_fill_color = comp_render[0][1]
                                        comp_border_color = comp_render[0][2]
                                        comp_border_width = comp_render[0][3]

                            else:# no layout info about compartment,
                                # then the whole size of the canvas is the compartment size
                                # modify the compartment size using the max_rec function above
                                # random assigned network:
                                # dimension = [800,800]
                                # position = [40,40]
                                # the whole size of the compartment: 4000*2500
                                dimension = [def_comp_width, def_comp_height]
                                position = [10,10]
                                comp_fill_color = (255, 255, 255, 255) #the last digit for transparent
                                comp_border_color = (255, 255, 255, 255)
                    
                            if comp_fill_color == (255, 255, 255, 255):
                                comp_fill_color = (255, 255, 255, 0)
                            if comp_border_color == (255, 255, 255, 255):
                                comp_border_color = (255, 255, 255, 0) 
                          
                            # position_abs = [abs(y) for y in position]
                            # position = position_abs
                       
                            position = [position[0]-TopLeft[0], position[1]-TopLeft[1]]
                            
                            if any(y < 0 for y in position):
                                raise Exception("SBcoyote requires positive positions.")


                            if temp_id in comp_specs_in_list: #consider the compartments with species inside
                            
                                if position[0] > def_canvas_width or position[1] > def_canvas_height: #beyond the canvas size
                                    shift = position
                                    position = [position[0]-shift[0], position[1]-shift[1]]
                                if len(comp_fill_color) == 3:
                                    comp_fill_color.append(255)
                                if len(comp_border_color) == 3:
                                    comp_border_color.append(255)
                                api.add_compartment(net_index, id=temp_id, volume = vol,
                                size=Vec2(dimension[0],dimension[1]),position=Vec2(position[0],position[1]),
                                fill_color = api.Color(comp_fill_color[0],comp_fill_color[1],comp_fill_color[2],comp_fill_color[3]),
                                border_color = api.Color(comp_border_color[0],comp_border_color[1],comp_border_color[2],comp_border_color[3]),
                                border_width = comp_border_width)

                    id_list = []
                    nodeIdx_list = [] #get_nodes idx do not follow the same order of add_node
                    nodeIdx_specGlyph_list = []
                    nodeIdx_specGlyph_alias_list = []
                    numSpec_in_reaction = len(spec_specGlyph_id_list) 
                    # orphan nodes have been considered, so numSpec_in_reaction should equals to numSpecGlyphs
                    for i in range (numSpec_in_reaction):
                        temp_id = spec_specGlyph_id_list[i][0]
                        temp_name = spec_name_list[i]
                        temp_SBO = spec_SBO_list[i]
                        temp_concentration = spec_concentration_list[i]
                        tempGlyph_id = spec_specGlyph_id_list[i][1]
                        dimension = spec_dimension_list[i]
                        position = spec_position_list[i]
                        text_content = spec_text_content_list[i]
                        # position_abs = [abs(y) for y in position]
                        # position = position_abs
                        position = [position[0]-TopLeft[0]-shift[0], position[1]-TopLeft[1]-shift[1]]
                        if any(y < 0 for y in position):
                            raise Exception("SBcoyote requires positive positions.")
                        text_alignment = spec_text_alignment_list[i]
                        text_position = spec_text_position_list[i]
                        comp_id = model.getCompartmentIdSpeciesIsIn(temp_id)
                        
                        for j in range(numFloatingNodes):
                            if temp_id == FloatingNodes_ids[j]:
                                if temp_id not in id_list:
                                    flag_local = 0
                                    for k in range(len(spec_render)):
                                        if temp_id == spec_render[k][0]:
                                            spec_fill_color = spec_render[k][1]
                                            spec_border_color = spec_render[k][2]
                                            spec_border_width = spec_render[k][3]
                                            shapeIdx = spec_render[k][4]
                                            flag_local = 1
                                    if flag_local == 0 and len(spec_render) != 1:
                                        for k in range(len(spec_render)):
                                            if spec_render[k][0] == '': #global render but not for all
                                                spec_fill_color = spec_render[k][1]
                                                spec_border_color = spec_render[k][2]
                                                spec_border_width = spec_render[k][3]
                                                shapeIdx = spec_render[k][4]
                                    if len(spec_render) == 1:
                                        if spec_render[0][0] == '': #global render
                                            spec_fill_color = spec_render[0][1]
                                            spec_border_color = spec_render[0][2]
                                            spec_border_width = spec_render[0][3]
                                            shapeIdx = spec_render[0][4]
                                    for k in range(len(text_render)):
                                        if tempGlyph_id == text_render[k][0]:
                                            text_line_color = text_render[k][1]
                                            text_line_width = text_render[k][2]
                                            text_font_size = text_render[k][3]
                                            [text_anchor, text_vanchor] = text_render[k][4]
                                            text_font_family = text_render[k][6]
                                    if len(text_render) == 1:
                                        if text_render[0][0] == '':#global render
                                            text_line_color = text_render[0][1]
                                            text_line_width = text_render[0][2]
                                            text_font_size = text_render[0][3]
                                            [text_anchor, text_vanchor] = text_render[0][4]
                                            text_font_family = text_render[0][6]
                                    if spec_border_width == 0.:
                                        spec_border_width = 0.001
                                        spec_border_color = spec_fill_color
                                    
                                    if len(spec_fill_color) == 3:
                                        spec_fill_color.append(255)
                                    if len(spec_border_color) == 3:
                                        spec_border_color.appen(255) 
                                    if len(text_line_color) == 3:
                                        text_line_color.append(255) 
                                    #print(shapeIdx)
                                    
                                    
                                    nodeIdx_temp = api.add_node(net_index, id=temp_id, floating_node = True,
                                    size=Vec2(dimension[0],dimension[1]), position=Vec2(position[0],position[1]),
                                    fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2],spec_fill_color[3]),
                                    border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2],spec_border_color[3]),
                                    border_width=spec_border_width, shape_index=shapeIdx, concentration = temp_concentration,
                                    node_name = temp_name, node_SBO = temp_SBO)
                                    
                                    api.set_node_shape_property(net_index, nodeIdx_temp, -1, "alignment", text_alignment)
                                    api.set_node_shape_property(net_index, nodeIdx_temp, -1, "position", text_position)
                                    api.set_node_shape_property(net_index, nodeIdx_temp, -1, "font_color", 
                                    api.Color(text_line_color[0], text_line_color[1], text_line_color[2], text_line_color[3]))
                                    api.set_node_shape_property(net_index, nodeIdx_temp, -1, "font_size", int(text_font_size))
                                    id_list.append(temp_id)
                                    nodeIdx_list.append(nodeIdx_temp)
                                    nodeIdx_specGlyph_list.append([nodeIdx_temp,tempGlyph_id])
                                                  
                               
                                else:
                                    index = id_list.index(temp_id)
                                    nodeIdx_temp = api.add_alias(net_index, original_index=index,
                                    size=Vec2(dimension[0],dimension[1]), position=Vec2(position[0],position[1]) )
                                    api.set_node_shape_property(net_index, nodeIdx_temp, -1, "alignment", text_alignment)
                                    api.set_node_shape_property(net_index, nodeIdx_temp, -1, "position", text_position)
                                    #api.set_node_shape_property(net_index, nodeIdx_temp, -1, "font_color", 
                                    #api.Color(text_line_color[0], text_line_color[1], text_line_color[2], text_line_color[3]))
                                    #api.set_node_shape_property(net_index, nodeIdx_temp, -1, "font_size", int(text_font_size))
                                    id_list.append(temp_id)
                                    nodeIdx_list.append(nodeIdx_temp)
                                    nodeIdx_specGlyph_alias_list.append([nodeIdx_temp,tempGlyph_id])
                                
                                comp_id = model.getCompartmentIdSpeciesIsIn(temp_id)
                                for xx in range(numComps):
                                    if comp_id == Comps_ids[xx]:
                                        try:
                                            api.set_compartment_of_node(net_index=net_index, node_index=nodeIdx_temp, comp_index=xx)
                                        except:
                                            pass 
                                for k in range(numCompGlyphs):
                                    if len(comp_id_list) !=0 and comp_id == comp_id_list[k]:
                                        comp_node_list[k].append(nodeIdx_temp)
                        for j in range(numBoundaryNodes):
                            if temp_id == BoundaryNodes_ids[j]:
                                if temp_id not in id_list:
                                    flag_local = 0
                                    for k in range(len(spec_render)):
                                        if temp_id == spec_render[k][0]:
                                            spec_fill_color = spec_render[k][1]
                                            spec_border_color = spec_render[k][2]
                                            spec_border_width = spec_render[k][3]
                                            shapeIdx = spec_render[k][4]
                                            flag_local = 1
                                    if flag_local == 0 and len(spec_render) != 1:
                                        for k in range(len(spec_render)):
                                            if spec_render[k][0] == '': #global render but not for all
                                                spec_fill_color = spec_render[k][1]
                                                spec_border_color = spec_render[k][2]
                                                spec_border_width = spec_render[k][3]
                                                shapeIdx = spec_render[k][4]
                                    if len(spec_render) == 1:
                                        if spec_render[0][0] == '': #global render
                                            spec_fill_color = spec_render[0][1]
                                            spec_border_color = spec_render[0][2]
                                            spec_border_width = spec_render[0][3]
                                            shapeIdx = spec_render[0][4]
                                    for k in range(len(text_render)):
                                        if tempGlyph_id == text_render[k][0]:
                                            text_line_color = text_render[k][1]
                                            text_line_width = text_render[k][2]  
                                            text_font_size = text_render[k][3] 
                                            [text_anchor, text_vanchor] = text_render[k][4] 
                                            text_font_family = text_render[k][6]
                                    if len(text_render) == 1:
                                        if text_render[0][0] == '':#global render
                                            text_line_color = text_render[0][1]
                                            text_line_width = text_render[0][2]
                                            text_font_size = text_render[0][3]
                                            [text_anchor, text_vanchor] = text_render[0][4] 
                                            text_font_family = text_render[0][6] 
                                    if spec_border_width == 0.:
                                        spec_border_width = 0.001
                                        spec_border_color = spec_fill_color
                                    if len(spec_fill_color) == 3:
                                        spec_fill_color.append(255)
                                    if len(spec_border_color) == 3:
                                        spec_border_color.appen(255) 
                                    if len(text_line_color) == 3:
                                        text_line_color.append(255)
                                    
                                    nodeIdx_temp = api.add_node(net_index, id=temp_id, floating_node = False,
                                    size=Vec2(dimension[0],dimension[1]), position=Vec2(position[0],position[1]),
                                    fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2],spec_fill_color[3]),
                                    border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2],spec_border_color[3]),
                                    border_width=spec_border_width, shape_index=shapeIdx, concentration = temp_concentration,
                                    node_name = temp_name, node_SBO = temp_SBO)
                                                                            
                                    api.set_node_shape_property(net_index, nodeIdx_temp, -1, "alignment", text_alignment)
                                    api.set_node_shape_property(net_index, nodeIdx_temp, -1, "position", text_position)
                                    api.set_node_shape_property(net_index, nodeIdx_temp, -1, "font_color", 
                                    api.Color(text_line_color[0], text_line_color[1], text_line_color[2], text_line_color[3]))
                                    api.set_node_shape_property(net_index, nodeIdx_temp, -1, "font_size", int(text_font_size))
                                    id_list.append(temp_id)
                                    nodeIdx_list.append(nodeIdx_temp)
                                    nodeIdx_specGlyph_list.append([nodeIdx_temp,tempGlyph_id])
    
                                else:
                                    index = id_list.index(temp_id)
                                    nodeIdx_temp = api.add_alias(net_index, original_index=index,
                                    size=Vec2(dimension[0],dimension[1]), position=Vec2(position[0],position[1]))
                                    api.set_node_shape_property(net_index, nodeIdx_temp, -1, "alignment", text_alignment)
                                    api.set_node_shape_property(net_index, nodeIdx_temp, -1, "position", text_position)
                                    #api.set_node_shape_property(net_index, nodeIdx_temp, -1, "font_color", 
                                    #api.Color(text_line_color[0], text_line_color[1], text_line_color[2], text_line_color[3]))
                                    #api.set_node_shape_property(net_index, nodeIdx_temp, -1, "font_size", int(text_font_size))
                                    id_list.append(temp_id)
                                    nodeIdx_list.append(nodeIdx_temp)
                                    nodeIdx_specGlyph_alias_list.append([nodeIdx_temp,tempGlyph_id])
                                
                                comp_id = model.getCompartmentIdSpeciesIsIn(temp_id)
                                for xx in range(numComps):
                                    if comp_id == Comps_ids[xx]: 
                                        try:           
                                            api.set_compartment_of_node(net_index=net_index, node_index=nodeIdx_temp, comp_index=xx)             
                                        except:
                                            pass                                   
                                for k in range(numCompGlyphs):
                                    if len(comp_id) != 0 and comp_id == comp_id_list[k]:
                                        comp_node_list[k].append(nodeIdx_temp)

                    if len(comp_id_list) != 0 or numComps != 0:
                        for i in range(numComps):
                            temp_id = Comps_ids[i]
                            if temp_id == '_compartment_default_': 
                                # #numNodes is different from len(nodeIdx_list) because of alias node
                                node_list_default = [item for item in range(len(nodeIdx_list))]
                                # for j in range(len(node_list_default)):
                                #     try:
                                #         api.set_compartment_of_node(net_index=net_index, node_index=node_list_default[j], comp_index=i)
                                #     except:
                                #         pass # Orphan nodes are removed
                                for j in range(len(node_list_default)):
                                    api.set_compartment_of_node(net_index=net_index, node_index=node_list_default[j], comp_index=-1)
                            for j in range(numCompGlyphs):
                                if comp_id_list[j] == temp_id:
                                    node_list_temp = comp_node_list[j]
                                else:
                                    node_list_temp = []
                        
                                for k in range(len(node_list_temp)):
                                    try:
                                        api.set_compartment_of_node(net_index=net_index, node_index=node_list_temp[k], comp_index=i)
                                    except:
                                        pass
                    else:
                        for i in range(len(nodeIdx_list)):
                            #api.set_compartment_of_node(net_index=net_index, node_index=nodeIdx_list[i], comp_index=0)
                            api.set_compartment_of_node(net_index=net_index, node_index=nodeIdx_list[i], comp_index=-1)

                    nodeIdx_specGlyph_whole_list = nodeIdx_specGlyph_list + nodeIdx_specGlyph_alias_list

                    dummy_node_id_index = 0
                    allNodes = api.get_nodes(net_index)
                    allCompartments = api.get_compartments(net_index)
                    for i in range (numReactionGlyphs):
                        src = []
                        dst = []
                        mod = []
                        mod_type = ModifierTipStyle.CIRCLE
                        src_handle = []
                        dst_handle = []
                        src_lineend_pos = []
                        dst_lineend_pos = []
                        temp_id = reaction_id_list[i]
                        kinetics = kinetics_list[i]
                        rct_num = len(rct_specGlyph_handle_list[i])
                        prd_num = len(prd_specGlyph_handle_list[i])
                        #mod_num = max(len(mod_specGlyph_list[i]),len(reaction_mod_list[i]))
                        mod_num = len(mod_specGlyph_list[i])
                        reaction_type = reaction_type_list[i]
                        
                        # for j in range(rct_num):
                        #     temp_specGlyph_id = rct_specGlyph_list[i][j]
                        #     for k in range(numSpec_in_reaction):
                        #         if temp_specGlyph_id == nodeIdx_specGlyph_whole_list[k][1]:
                        #             rct_idx = nodeIdx_specGlyph_whole_list[k][0]
                                    
                        #     src.append(rct_idx)

                        # for j in range(prd_num):
                        #     temp_specGlyph_id = prd_specGlyph_list[i][j]
                        #     for k in range(numSpec_in_reaction):
                        #         if temp_specGlyph_id == nodeIdx_specGlyph_whole_list[k][1]:
                        #             prd_idx = nodeIdx_specGlyph_whole_list[k][0]
                        #     dst.append(prd_idx)
                        if rct_num != 0 or prd_num != 0:
                            for j in range(rct_num):
                                temp_specGlyph_id = rct_specGlyph_handle_list[i][j][0]
                                for k in range(numSpec_in_reaction):
                                    if temp_specGlyph_id == nodeIdx_specGlyph_whole_list[k][1]:
                                        rct_idx = nodeIdx_specGlyph_whole_list[k][0]
                                src.append(rct_idx)
                                src_handle.append(rct_specGlyph_handle_list[i][j][1])
                                src_lineend_pos.append(rct_specGlyph_handle_list[i][j][3])
                           
                            
                            for j in range(prd_num):
                                temp_specGlyph_id = prd_specGlyph_handle_list[i][j][0]
                                for k in range(numSpec_in_reaction):
                                    if temp_specGlyph_id == nodeIdx_specGlyph_whole_list[k][1]:
                                        prd_idx = nodeIdx_specGlyph_whole_list[k][0]
                                dst.append(prd_idx)
                                dst_handle.append(prd_specGlyph_handle_list[i][j][1])
                                dst_lineend_pos.append(prd_specGlyph_handle_list[i][j][3])

                            for j in range(mod_num):
                                if len(mod_specGlyph_list[i]) != 0:
                                    temp_specGlyph_id = mod_specGlyph_list[i][j][0]
                                    for k in range(numSpec_in_reaction):
                                        if temp_specGlyph_id == nodeIdx_specGlyph_whole_list[k][1]:
                                            mod_idx = nodeIdx_specGlyph_whole_list[k][0]
                                    mod.append(mod_idx)
                                    if mod_specGlyph_list[i][j][1] == "inhibitor":
                                        mod_type = ModifierTipStyle.TEE
                                else:
                                    for k in range(len(spec_specGlyph_id_list)):
                                        if reaction_mod_list[i][j] == spec_specGlyph_id_list[k][0]:
                                            temp_specGlyph_id = spec_specGlyph_id_list[k][1]
                                    for k in range(numSpec_in_reaction):
                                        if temp_specGlyph_id == nodeIdx_specGlyph_whole_list[k][1]:
                                            mod_idx = nodeIdx_specGlyph_whole_list[k][0]
                                    mod.append(mod_idx)
                                    
                        else:
                            rct_num = model.getNumReactants(i)
                            prd_num = model.getNumProducts(i)
                            mod_num = model.getNumModifiers(temp_id)
                    
                            for j in range(rct_num):
                                rct_id = model.getReactant(temp_id,j)
                                for k in range(len(spec_specGlyph_id_list)):
                                    if spec_specGlyph_id_list[k][0] == rct_id:
                                        tempGlyph_id = spec_specGlyph_id_list[k][1]
                                for k in range(numSpec_in_reaction):
                                    if nodeIdx_specGlyph_whole_list[k][1] == tempGlyph_id:
                                        rct_idx = nodeIdx_specGlyph_whole_list[k][0]
                                src.append(rct_idx)
                                #src_handle.append(rct_specGlyph_handle_list[i][j][1])

                            for j in range(prd_num):
                                prd_id = model.getProduct(temp_id,j)
                                for k in range(len(spec_specGlyph_id_list)):
                                    if spec_specGlyph_id_list[k][0] == prd_id:
                                        tempGlyph_id = spec_specGlyph_id_list[k][1]
                                for k in range(numSpec_in_reaction):
                                    if nodeIdx_specGlyph_whole_list[k][1] == tempGlyph_id:
                                        prd_idx = nodeIdx_specGlyph_whole_list[k][0]
                                dst.append(prd_idx)
                                #dst_handle.append(prd_specGlyph_handle_list[i][j][1])

                            #modifiers = model.getListOfModifiers(temp_id) 
                            #simple sbml bug with repeated first modifiers
                            reaction = model_layout.getReaction(temp_id)
                            modifiers = []
                            for j in range(len(reaction.getListOfModifiers())):
                                modSpecRef = reaction.getModifier(j)
                                modifiers.append(modSpecRef.getSpecies())

                            #parameter in kinetic law 
                            try:  
                                kineticLaw = reaction.getKineticLaw()
                                kinetic_parameter_list = []
                                kinetic_parameter_value_list = []
                                for j in range(len(kineticLaw.getListOfParameters())):
                                    parameter = kineticLaw.getParameter(j)
                                    name = parameter.getName()
                                    if parameter.isSetValue():
                                        value = kineticLaw.getParameter(j).getValue()
                                    else:
                                        value = 0.
                                    kinetic_parameter_list.append(name)
                                    kinetic_parameter_value_list.append(value)
                                for j in range(len(kinetic_parameter_list)):
                                    p = kinetic_parameter_list[j]
                                    v = kinetic_parameter_value_list[j]
                                    try:
                                        api.set_parameter_value(net_index, p, v)
                                    except:
                                        pass
                            except:
                                pass


                            for j in range(mod_num):
                                mod_id = modifiers[j]
                                for k in range(len(spec_specGlyph_id_list)):
                                    if spec_specGlyph_id_list[k][0] == mod_id:
                                        tempGlyph_id = spec_specGlyph_id_list[k][1]
                                for k in range(numSpec_in_reaction):
                                    if nodeIdx_specGlyph_whole_list[k][1] == tempGlyph_id:
                                        mod_idx = nodeIdx_specGlyph_whole_list[k][0]
                                mod.append(mod_idx)

                        mod = set(mod)

                        for j in range(len(rxn_render)):
                            if temp_id == rxn_render[j][0]:
                                reaction_line_color = rxn_render[j][1]
                                reaction_line_width = rxn_render[j][2]
                        if len(rxn_render) == 1:
                            if rxn_render[0][0] == '':#global render
                                reaction_line_color = rxn_render[0][1]
                                reaction_line_width = rxn_render[0][2]

                        try:
                            src_corr = []
                            [src_corr.append(x) for x in src if x not in src_corr]
                            dst_corr = []
                            [dst_corr.append(x) for x in dst if x not in dst_corr]

                            
                            center_position = reaction_center_list[i] 
                            center_handle = reaction_center_handle_list[i]
                        
                            center_position = [center_position[0]-TopLeft[0]-shift[0], center_position[1]-TopLeft[1]-shift[1]]
                            center_handle = [center_handle[0]-TopLeft[0]-shift[0], center_handle[1]-TopLeft[1]-shift[1]]
                        
                            if center_handle != []:
                                handles = [center_handle]
                            else:
                                handles = [center_position]
                            
                            src_handle_shift = []
                            dst_handle_shift = []
                            for a in range(len(src_handle)):
                                src_handle_shift.append([src_handle[a][0]-TopLeft[0]-shift[0], src_handle[a][1]-TopLeft[1]-shift[1]])
                            for a in range(len(dst_handle)):
                                dst_handle_shift.append([dst_handle[a][0]-TopLeft[0]-shift[0], dst_handle[a][1]-TopLeft[1]-shift[1]])
                            
                            if len(src_corr) == 0:
                                temp_node_id = "dummy" + str(dummy_node_id_index)                   
                                comp_node_id = allNodes[dst_corr[0]].id 
                                dst_node_id = comp_node_id #pick a product node
                                # assume the dummy node is in the same compartment as the first src/dst node
                                comp_id = model.getCompartmentIdSpeciesIsIn(comp_node_id)
                                for m in range(len(allCompartments)):
                                    if comp_id == allCompartments[m].id:
                                        comp_position = allCompartments[m].position
                                        comp_size = allCompartments[m].size
                                        compColor = allCompartments[m].fill_color
                                        comp_fill_color = [compColor.r, compColor.g, compColor.b, compColor.a]
                                        spec_fill_color = comp_fill_color
                                        spec_border_color = comp_fill_color
                                        text_line_color = comp_fill_color
                                for m in range(len(allNodes)):
                                    if dst_node_id == allNodes[m].id:
                                        dst_node_pos = allNodes[m].position
                                        dst_node_size = allNodes[m].size
                                        dst_node_c_pos = [dst_node_pos[0]+0.5*dst_node_size[0],
                                                            dst_node_pos[1]+0.5*dst_node_size[1]]
                                if spec_border_width == 0.:
                                    spec_border_width = 0.001
                                    spec_border_color = spec_fill_color


                                #node_position = [comp_position[0] + math.trunc (_random.random()*(comp_size[0] - 60.)), 
                                #                comp_position[1] + math.trunc (_random.random()*(comp_size[1] - 40.))]
                                node_position = center_position
                                nodeIdx_temp = api.add_node(net_index, id=temp_node_id, size=Vec2(0.5*reaction_line_width,0.5*reaction_line_width), floating_node = True,
                                position=Vec2(node_position[0], node_position[1]),
                                fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2],spec_fill_color[3]),
                                border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2],spec_border_color[3]),
                                border_width=spec_border_width, shape_index=shapeIdx)
                                api.set_node_shape_property(net_index, nodeIdx_temp, -1, "font_color", 
                                    api.Color(text_line_color[0], text_line_color[1], text_line_color[2], text_line_color[3]))

                                src_corr.append(nodeIdx_temp)
                                dummy_node_id_index += 1

                                #dummy_handle_position = [0.5*(node_position[0] + center_position[0]), 
                                #                            0.5*(node_position[1] + center_position[1])]
                                dummy_handle_position = [0.5*(dst_node_c_pos[0] + center_position[0]), 
                                                            0.5*(dst_node_c_pos[1] + center_position[1])]
                                #dummy_handle_position = center_position
                                center_position = dummy_handle_position
                                src_handle_shift.append(dummy_handle_position)

                                for xx in range(numComps):
                                    if comp_id == Comps_ids[xx]:
                                        api.set_compartment_of_node(net_index=net_index, node_index=nodeIdx_temp, comp_index=xx)
                            
                            if len(dst_corr) == 0:
                                temp_node_id = "dummy" + str(dummy_node_id_index)                   
                                comp_node_id = allNodes[src_corr[0]].id
                                src_node_id = comp_node_id #pick a rct node
                                if allNodes[src_corr[0]].original_index == -1:
                                    for m in range(len(allNodes)):
                                        if src_node_id == allNodes[m].id:
                                            src_node_pos = allNodes[m].position
                                            src_node_size = allNodes[m].size
                                            src_node_c_pos = [src_node_pos[0]+0.5*src_node_size[0],
                                                            src_node_pos[1]+0.5*src_node_size[1]]
                                else:
                                    src_node_idx = src_corr[0]#alias node
                                    for m in range(len(nodeIdx_specGlyph_whole_list)):
                                        if src_node_idx == nodeIdx_specGlyph_whole_list[m][0]:
                                            src_node_Glyph_id = nodeIdx_specGlyph_whole_list[m][1]
                                    for m in range(len(spec_specGlyph_id_list)):
                                        if src_node_Glyph_id == spec_specGlyph_id_list[m][1]:
                                            #print(spec_specGlyph_id_list[m][0])
                                            src_node_size = spec_dimension_list[m]
                                            src_node_pos = spec_position_list[m]
                                            src_node_c_pos = [src_node_pos[0]+0.5*src_node_size[0],
                                                                src_node_pos[1]+0.5*src_node_size[1]]
                                    
                                # try:#in case the dummy node has an alias node as src node
                                #     src_node_c_pos = src_lineend_pos[0]
                                # except:#in case there is no lineending available
                                #     src_node_id = comp_node_id #pick a rct node
                                #     for m in range(len(allNodes)):
                                #         if src_node_id == allNodes[m].id:
                                #             src_node_pos = allNodes[m].position
                                #             src_node_size = allNodes[m].size
                                #             src_node_c_pos = [src_node_pos[0]+0.5*src_node_size[0],
                                #                               src_node_pos[1]+0.5*src_node_size[1]]
                            
                                comp_id = model.getCompartmentIdSpeciesIsIn(comp_node_id)
                                for m in range(len(allCompartments)):
                                    if comp_id == allCompartments[m].id:
                                        comp_position = allCompartments[m].position
                                        comp_size = allCompartments[m].size
                                        compColor = allCompartments[m].fill_color
                                        comp_fill_color = [compColor.r, compColor.g, compColor.b, compColor.a]
                                        spec_fill_color = comp_fill_color
                                        spec_border_color = comp_fill_color
                                        text_line_color = comp_fill_color
                    
                                if spec_border_width == 0.:
                                    spec_border_width = 0.001
                                    spec_border_color = spec_fill_color
                                
                                #node_position = [comp_position[0] + math.trunc (_random.random()*(comp_size[0]-60.)), 
                                #                comp_position[1] + math.trunc (_random.random()*(comp_size[1]-40.))]
                                node_position = center_position
                                
                                nodeIdx_temp = api.add_node(net_index, id=temp_node_id, size=Vec2(0.5*reaction_line_width,0.5*reaction_line_width), floating_node = True,
                                position=Vec2(node_position[0], node_position[1]),
                                fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2],spec_fill_color[3]),
                                border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2],spec_border_color[3]),
                                border_width=spec_border_width, shape_index=shapeIdx)
                                api.set_node_shape_property(net_index, nodeIdx_temp, -1, "font_color", 
                                    api.Color(text_line_color[0], text_line_color[1], text_line_color[2], text_line_color[3]))
                                
                                dst_corr.append(nodeIdx_temp)
                                dummy_node_id_index += 1

                                #dummy_handle_position = [0.5*(node_position[0] + center_position[0]), 
                                #                            0.5*(node_position[1] + center_position[1])]
                                
                                dummy_handle_position = [0.5*(src_node_c_pos[0] + center_position[0]), 
                                                            0.5*(src_node_c_pos[1] + center_position[1])]
                                #dummy_handle_position = center_position
                                center_position = dummy_handle_position
                                dst_handle_shift.append(dummy_handle_position)

                                for xx in range(numComps):
                                    if comp_id == Comps_ids[xx]:
                                        api.set_compartment_of_node(net_index=net_index, node_index=nodeIdx_temp, comp_index=xx)

                            #add_reaction might automatically sort the index of reactants and products
                            src_handle_shift = [x for _,x in sorted(zip(src_corr, src_handle_shift))]
                            dst_handle_shift = [x for _,x in sorted(zip(dst_corr, dst_handle_shift))]
                            src_corr.sort()
                            dst_corr.sort()


                            handles.extend(src_handle_shift)
                            handles.extend(dst_handle_shift)
                            
                            if len(reaction_line_color) == 3:
                                reaction_line_color.append(255)
                            idx = api.add_reaction(net_index, id=temp_id, 
                            reactants=src_corr, products=dst_corr,
                            fill_color=api.Color(reaction_line_color[0],reaction_line_color[1],reaction_line_color[2],reaction_line_color[3]),
                            line_thickness=reaction_line_width, 
                            modifiers = mod)
                            
                            api.update_reaction(net_index, idx, ratelaw = kinetics)
                            if reaction_type == False:
                                api.update_reaction(net_index, idx, 
                                center_pos = Vec2(center_position[0],center_position[1]),
                                use_bezier = reaction_type)
                            else:
                                handles_Vec2 = [] 
                                if [] not in handles:      
                                    for i in range(len(handles)):
                                        handles_Vec2.append(Vec2(handles[i][0],handles[i][1]))
                                    api.update_reaction(net_index, idx, center_pos = Vec2(center_position[0],center_position[1]),
                                    handle_positions=handles_Vec2)
                            api.update_reaction(net_index, idx, modifier_tip_style = mod_type)  
                            
                        except: #There is no info about the center/handle positions, so set as default 
                            src_corr = []
                            [src_corr.append(x) for x in src if x not in src_corr]
                            dst_corr = []
                            [dst_corr.append(x) for x in dst if x not in dst_corr]

                            #set the information for handle positions, center positions look as straight line
                            #the default positions of center and handles positions sometimes look quite strange.
                        
                            center_x = 0.
                            center_y = 0.
                            allNodes = api.get_nodes(net_index)
                            rct_num = len(src_corr)
                            prd_num = len(dst_corr)
                            for j in range(rct_num):
                                src_position = allNodes[src_corr[j]].position
                                src_dimension = allNodes[src_corr[j]].size
                                src_position = [src_position[0]-TopLeft[0]-shift[0], src_position[1]-TopLeft[1]-shift[1]]
                                center_x += src_position[0]+.5*src_dimension[0]
                                center_y += src_position[1]+.5*src_dimension[1]
                            for j in range(prd_num):
                                dst_position = allNodes[dst_corr[j]].position
                                dst_dimension = allNodes[dst_corr[j]].size
                                dst_position = [dst_position[0]-TopLeft[0]-shift[0], dst_position[1]-TopLeft[1]-shift[1]]
                                center_x += dst_position[0]+.5*dst_dimension[0]
                                center_y += dst_position[1]+.5*dst_dimension[1]
                            center_x = center_x/(rct_num + prd_num) 
                            center_y = center_y/(rct_num + prd_num)
                            center_position = [center_x, center_y]
                            handles = [center_position]

                            src_handles = []
                            dst_handles = []
                            for j in range(rct_num):
                                src_position = allNodes[src_corr[j]].position
                                src_dimension = allNodes[src_corr[j]].size
                                src_handle_x = .5*(center_position[0] + src_position[0] + .5*src_dimension[0])
                                src_handle_y = .5*(center_position[1] + src_position[1] + .5*src_dimension[1])
                                src_handles.append([src_handle_x,src_handle_y])
                            for j in range(prd_num):
                                dst_position = allNodes[dst_corr[j]].position
                                dst_dimension = allNodes[dst_corr[j]].size
                                dst_handle_x = .5*(center_position[0] + dst_position[0] + .5*dst_dimension[0])
                                dst_handle_y = .5*(center_position[1] + dst_position[1] + .5*dst_dimension[1])
                                dst_handles.append([dst_handle_x,dst_handle_y])


                            if len(src_corr) == 0:
                                temp_node_id = "dummy" + str(dummy_node_id_index)                   
                                comp_node_id = allNodes[dst_corr[0]].id 

                                dst_node_id = comp_node_id #pick a product node
                                # assume the dummy node is in the same compartment as the first src/dst node
                                comp_id = model.getCompartmentIdSpeciesIsIn(comp_node_id)
                                for m in range(len(allCompartments)):
                                    if comp_id == allCompartments[m].id:
                                        comp_position = allCompartments[m].position
                                        comp_size = allCompartments[m].size
                                        compColor = allCompartments[m].fill_color
                                        comp_fill_color = [compColor.r, compColor.g, compColor.b, compColor.a]
                                        spec_fill_color = comp_fill_color
                                        spec_border_color = comp_fill_color
                                        text_line_color = comp_fill_color
                                for m in range(len(allNodes)):
                                    if dst_node_id == allNodes[m].id:
                                        dst_node_pos = allNodes[m].position
                                        dst_node_size = allNodes[m].size
                                        dst_node_c_pos = [dst_node_pos[0]+0.5*dst_node_size[0],
                                                          dst_node_pos[1]+0.5*dst_node_size[1]]
                                if spec_border_width == 0.:
                                    spec_border_width = 0.001
                                    spec_border_color = spec_fill_color


                                #node_position = [comp_position[0] + math.trunc (_random.random()*(comp_size[0] - 60.)), 
                                #                comp_position[1] + math.trunc (_random.random()*(comp_size[1] - 40.))]
                                node_position = center_position
                                nodeIdx_temp = api.add_node(net_index, id=temp_node_id, size=Vec2(0.5*reaction_line_width,0.5*reaction_line_width), floating_node = True,
                                position=Vec2(node_position[0], node_position[1]),
                                fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2],spec_fill_color[3]),
                                border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2],spec_border_color[3]),
                                border_width=spec_border_width, shape_index=shapeIdx)
                                api.set_node_shape_property(net_index, nodeIdx_temp, -1, "font_color", 
                                    api.Color(text_line_color[0], text_line_color[1], text_line_color[2], text_line_color[3]))

                                src_corr.append(nodeIdx_temp)
                                dummy_node_id_index += 1

                                #dummy_handle_position = [0.5*(node_position[0] + center_position[0]), 
                                #                            0.5*(node_position[1] + center_position[1])]
                                dummy_handle_position = [0.5*(dst_node_c_pos[0] + center_position[0]), 
                                                            0.5*(dst_node_c_pos[1] + center_position[1])]
                                #dummy_handle_position = center_position
                                center_position = dummy_handle_position
                                src_handles.append(dummy_handle_position)

                                for xx in range(numComps):
                                    if comp_id == Comps_ids[xx]:
                                        api.set_compartment_of_node(net_index=net_index, node_index=nodeIdx_temp, comp_index=xx)
                            

                            if len(dst_corr) == 0:
                                temp_node_id = "dummy" + str(dummy_node_id_index)                   
                                comp_node_id = allNodes[src_corr[0]].id

                                src_node_id = comp_node_id #pick a rct node
                                comp_id = model.getCompartmentIdSpeciesIsIn(comp_node_id)
                                for m in range(len(allCompartments)):
                                    if comp_id == allCompartments[m].id:
                                        comp_position = allCompartments[m].position
                                        comp_size = allCompartments[m].size
                                        compColor = allCompartments[m].fill_color
                                        comp_fill_color = [compColor.r, compColor.g, compColor.b, compColor.a]
                                        spec_fill_color = comp_fill_color
                                        spec_border_color = comp_fill_color
                                        text_line_color = comp_fill_color
                                for m in range(len(allNodes)):
                                    if src_node_id == allNodes[m].id:
                                        src_node_pos = allNodes[m].position
                                        src_node_size = allNodes[m].size
                                        src_node_c_pos = [src_node_pos[0]+0.5*src_node_size[0],
                                                          src_node_pos[1]+0.5*src_node_size[1]]
                                if spec_border_width == 0.:
                                    spec_border_width = 0.001
                                    spec_border_color = spec_fill_color
                                
                                #node_position = [comp_position[0] + math.trunc (_random.random()*(comp_size[0]-60.)), 
                                #                comp_position[1] + math.trunc (_random.random()*(comp_size[1]-40.))]
                                node_position = center_position
                                nodeIdx_temp = api.add_node(net_index, id=temp_node_id, size=Vec2(0.5*reaction_line_width,0.5*reaction_line_width), floating_node = True,
                                position=Vec2(node_position[0], node_position[1]),
                                fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2],spec_fill_color[3]),
                                border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2],spec_border_color[3]),
                                border_width=spec_border_width, shape_index=shapeIdx)
                                api.set_node_shape_property(net_index, nodeIdx_temp, -1, "font_color", 
                                    api.Color(text_line_color[0], text_line_color[1], text_line_color[2], text_line_color[3]))
                                
                                dst_corr.append(nodeIdx_temp)
                                dummy_node_id_index += 1

                                #dummy_handle_position = [0.5*(node_position[0] + center_position[0]), 
                                #                            0.5*(node_position[1] + center_position[1])]
                                dummy_handle_position = [0.5*(src_node_c_pos[0] + center_position[0]), 
                                                            0.5*(src_node_c_pos[1] + center_position[1])]
                                #dummy_handle_position = center_position
                                center_position = dummy_handle_position
                                dst_handles.append(dummy_handle_position)

                                for xx in range(numComps):
                                    if comp_id == Comps_ids[xx]:
                                        api.set_compartment_of_node(net_index=net_index, node_index=nodeIdx_temp, comp_index=xx)



                            src_handles = [x for _,x in sorted(zip(src_corr, src_handles))]
                            dst_handles = [x for _,x in sorted(zip(dst_corr, dst_handles))]
                            src_corr.sort()
                            dst_corr.sort()

                            handles.extend(src_handles)
                            handles.extend(dst_handles)

                            if len(reaction_line_color)==3:
                                reaction_line_color.append(255)
                    
                            try: 
                                idx = api.add_reaction(net_index, id=temp_id, reactants=src_corr, products=dst_corr,
                                fill_color=api.Color(reaction_line_color[0],reaction_line_color[1],reaction_line_color[2],reaction_line_color[3]),
                                line_thickness=reaction_line_width, modifiers = mod)
                                api.update_reaction(net_index, idx, ratelaw = kinetics,
                                fill_color=api.Color(reaction_line_color[0],reaction_line_color[1],reaction_line_color[2],reaction_line_color[3]))
                            except:
                                #rxn_id_duplicated
                                idx = api.add_reaction(net_index, id=temp_id + "_duplicate", reactants=src_corr, products=dst_corr,
                                fill_color=api.Color(reaction_line_color[0],reaction_line_color[1],reaction_line_color[2],reaction_line_color[3]),
                                line_thickness=reaction_line_width, modifiers = mod)
                                api.update_reaction(net_index, idx, ratelaw = kinetics,
                                fill_color=api.Color(reaction_line_color[0],reaction_line_color[1],reaction_line_color[2],reaction_line_color[3]))
                                                             
                            api.update_reaction(net_index, idx, 
                                 center_pos = Vec2(center_position[0],center_position[1]),  
                                 fill_color=api.Color(reaction_line_color[0],reaction_line_color[1],reaction_line_color[2],reaction_line_color[3]))

                            handles_Vec2 = []  
                            if [] not in handles:      
                                for i in range(len(handles)):
                                    handles_Vec2.append(Vec2(handles[i][0],handles[i][1]))
                                api.update_reaction(net_index, idx, 
                                center_pos = Vec2(center_position[0],center_position[1]), 
                                handle_positions=handles_Vec2, 
                                fill_color=api.Color(reaction_line_color[0],reaction_line_color[1],reaction_line_color[2],reaction_line_color[3]))
                            
                            api.update_reaction(net_index, idx, modifier_tip_style = mod_type)

                else: # there is no layout information, assign position randomly and size as default
                    
                    comp_id_list = Comps_ids

                    for i in range(numComps):
                        temp_id = Comps_ids[i]
                        vol= model.getCompartmentVolume(i)
                        if math.isnan(vol):
                            vol = 1.
                        dimension = [800 + 100, 800 + 100]
                        position = [40,40]

                        api.add_compartment(net_index, id=temp_id, volume = vol,
                        size=Vec2(dimension[0],dimension[1]),position=Vec2(position[0],position[1]),
                        fill_color = api.Color(comp_fill_color[0],comp_fill_color[1],comp_fill_color[2],comp_fill_color[3]),
                        border_color = api.Color(comp_border_color[0],comp_border_color[1],comp_border_color[2],comp_border_color[3]),
                        border_width = comp_border_width)

                    # for i in range (numFloatingNodes):
                    #     temp_id = FloatingNodes_ids[i]
                    #     comp_id = model.getCompartmentIdSpeciesIsIn(temp_id)
                    #     try:
                    #         temp_concentration = model.getSpeciesInitialConcentration(temp_id)
                    #         if math.nan(temp_concentration):
                    #             temp_concentration = 1
                    #     except:
                    #         temp_concentration = 1.
                    #     if spec_border_width == 0.:
                    #         spec_border_width = 0.001
                    #         spec_border_color = spec_fill_color
                    #     nodeIdx_temp = api.add_node(net_index, id=temp_id, size=Vec2(60,40), floating_node = True,
                    #     position=Vec2(40 + math.trunc (_random.random()*800), 40 + math.trunc (_random.random()*800)),
                    #     fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2],spec_fill_color[3]),
                    #     border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2],spec_border_color[3]),
                    #     border_width=spec_border_width, shape_index=shapeIdx, concentration=temp_concentration)
                    #     for j in range(numComps):
                    #         if comp_id == comp_id_list[j]:
                    #             comp_node_list[j].append(nodeIdx_temp)

                    # for i in range (numBoundaryNodes):
                    #     temp_id = BoundaryNodes_ids[i]
                    #     comp_id = model.getCompartmentIdSpeciesIsIn(temp_id)
                    #     try:
                    #         temp_concentration = model.getSpeciesInitialConcentration(temp_id)
                    #         if math.nan(temp_concentration):
                    #             temp_concentration = 1
                    #     except:
                    #         temp_concentration = 1.0
                    #     if spec_border_width == 0.:
                    #         spec_border_width = 0.001
                    #         spec_border_color = spec_fill_color
                    #     nodeIdx_temp = api.add_node(net_index, id=temp_id, size=Vec2(60,40), floating_node = False,
                    #     position=Vec2(40 + math.trunc (_random.random()*800), 40 + math.trunc (_random.random()*800)),
                    #     fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2],spec_fill_color[3]),
                    #     border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2],spec_border_color[3]),
                    #     border_width=spec_border_width, shape_index=shapeIdx, concentration=temp_concentration)
                    #     for j in range(numComps):
                    #         if comp_id == comp_id_list[j]:
                    #             comp_node_list[j].append(nodeIdx_temp)

                    for i in range (numNodes):
                        temp_id = Nodes_ids[i]
                        comp_id = model.getCompartmentIdSpeciesIsIn(temp_id)
                        try:
                            temp_concentration = model.getSpeciesInitialConcentration(temp_id)
                            if math.nan(temp_concentration):
                                temp_concentration = 1
                        except:
                            temp_concentration = 1.
                        if spec_border_width == 0.:
                            spec_border_width = 0.001
                            spec_border_color = spec_fill_color
                        node_status = True
                        for j in range(numBoundaryNodes):
                            temp_b_id = BoundaryNodes_ids[j]
                            if temp_id == temp_b_id:
                                node_status = False
                        nodeIdx_temp = api.add_node(net_index, id=temp_id, size=Vec2(60,40), floating_node = node_status,
                        position=Vec2(40 + math.trunc (_random.random()*800), 40 + math.trunc (_random.random()*800)),
                        fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2],spec_fill_color[3]),
                        border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2],spec_border_color[3]),
                        border_width=spec_border_width, shape_index=shapeIdx, concentration=temp_concentration)
                        for j in range(numComps):
                            if comp_id == comp_id_list[j]:
                                comp_node_list[j].append(nodeIdx_temp)


                    for i in range(numComps):
                        temp_id = Comps_ids[i]
                        for j in range(numComps):
                            if comp_id_list[j] == temp_id:
                                node_list_temp = comp_node_list[j]
                            for k in range(len(node_list_temp)):
                                api.set_compartment_of_node(net_index=net_index, node_index=node_list_temp[k], comp_index=i)

                    numNodes = api.node_count(net_index)
                    allNodes = api.get_nodes(net_index)


                    flag_add_rxn_err = 0
                    dummy_node_id_index = 0
                    for i in range (numRxns):
                        src = []
                        dst = []
                        mod = []
                        temp_id = Rxns_ids[i]
                        try: 
                            kinetics = model.getRateLaw(i)
                            if len(function_definitions) > 0:
                                #kinetics = _expandFormula(kinetics, function_definitions)
                                kinetics = ""
                        except:
                            kinetics = ""
                    
                        rct_num = model.getNumReactants(temp_id)
                        prd_num = model.getNumProducts(temp_id)
                        mod_num = model.getNumModifiers(temp_id)

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

                        #modifiers = model.getListOfModifiers(temp_id)
                        #simple sbml bug with repeated first modifiers
                        reaction = model_layout.getReaction(temp_id)
                        modifiers = []
                        for j in range(len(reaction.getListOfModifiers())):
                           modSpecRef = reaction.getModifier(j)
                           modifiers.append(modSpecRef.getSpecies())

                        #parameter in kinetic law
                        try:
                            kineticLaw = reaction.getKineticLaw()
                            kinetic_parameter_list = []
                            kinetic_parameter_value_list = []
                            for j in range(len(kineticLaw.getListOfParameters())):
                                parameter = kineticLaw.getParameter(j)
                                name = parameter.getName()
                                if parameter.isSetValue():
                                    value = kineticLaw.getParameter(j).getValue()
                                else:
                                    value = 0.
                                kinetic_parameter_list.append(name)
                                kinetic_parameter_value_list.append(value)
                            for j in range(len(kinetic_parameter_list)):
                                p = kinetic_parameter_list[j]
                                v = kinetic_parameter_value_list[j]
                                try:
                                    api.set_parameter_value(net_index, p, v)
                                except:
                                    pass
                        except:
                            pass

                        for j in range(mod_num):
                            mod_id = modifiers[j]
                            for k in range(numNodes):
                                if allNodes[k].id == mod_id:
                                    mod.append(allNodes[k].index) 
                   
                        try: 
                            src_corr = []
                            [src_corr.append(x) for x in src if x not in src_corr]

                            dst_corr = []
                            [dst_corr.append(x) for x in dst if x not in dst_corr]

                            if len(src_corr) == 0:
                                temp_node_id = "dummy" + str(dummy_node_id_index)                   
                                comp_node_id = allNodes[dst_corr[0]].id 
                                # assume the dummy node is in the same compartment as the first src/dst node
                                comp_id = model.getCompartmentIdSpeciesIsIn(comp_node_id)
                                if spec_border_width == 0.:
                                    spec_border_width = 0.001
                                    spec_border_color = spec_fill_color
                                nodeIdx_temp = api.add_node(net_index, id=temp_node_id, size=Vec2(60,40), floating_node = True,
                                position=Vec2(40 + math.trunc (_random.random()*800), 40 + math.trunc (_random.random()*800)),
                                fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2],spec_fill_color[3]),
                                border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2],spec_border_color[3]),
                                border_width=spec_border_width, shape_index=shapeIdx)
                                
                                src_corr.append(nodeIdx_temp)
                                dummy_node_id_index += 1

                                for xx in range(numComps):
                                    if comp_id == Comps_ids[xx]:
                                        api.set_compartment_of_node(net_index=net_index, node_index=nodeIdx_temp, comp_index=xx)
                            
                            if len(dst_corr) == 0:
                                temp_node_id = "dummy" + str(dummy_node_id_index)                   
                                comp_node_id = allNodes[src_corr[0]].id
                                comp_id = model.getCompartmentIdSpeciesIsIn(comp_node_id)
                                if spec_border_width == 0.:
                                    spec_border_width = 0.001
                                    spec_border_color = spec_fill_color
                                nodeIdx_temp = api.add_node(net_index, id=temp_node_id, size=Vec2(60,40), floating_node = True,
                                position=Vec2(40 + math.trunc (_random.random()*800), 40 + math.trunc (_random.random()*800)),
                                fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2],spec_fill_color[3]),
                                border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2],spec_border_color[3]),
                                border_width=spec_border_width, shape_index=shapeIdx)
                                
                                dst_corr.append(nodeIdx_temp)
                                dummy_node_id_index += 1

                                for xx in range(numComps):
                                    if comp_id == Comps_ids[xx]:
                                        api.set_compartment_of_node(net_index=net_index, node_index=nodeIdx_temp, comp_index=xx)

                            #add_reaction function will automatically sort src_corr and dst_corr,
                            #otherwise sometimes the handles are wrong 
                            src_corr.sort()
                            dst_corr.sort()

                            idx = api.add_reaction(net_index, id=temp_id, reactants=src_corr, products=dst_corr,
                            fill_color=api.Color(reaction_line_color[0],reaction_line_color[1],reaction_line_color[2],reaction_line_color[3]),
                            line_thickness=reaction_line_width, modifiers = mod)
                            api.update_reaction(net_index, idx, ratelaw = kinetics,
                            fill_color=api.Color(reaction_line_color[0],reaction_line_color[1],reaction_line_color[2],reaction_line_color[3]))


                            #set the information for handle positions, center positions look as straight line
                            #the default positions of center and handles positions sometimes look quite strange.
                        
                            center_x = 0.
                            center_y = 0.
                            rct_num = len(src_corr)
                            prd_num = len(dst_corr)
                            for j in range(rct_num):
                                src_position = allNodes[src_corr[j]].position
                                src_dimension = allNodes[src_corr[j]].size
                                center_x += src_position[0]+.5*src_dimension[0]
                                center_y += src_position[1]+.5*src_dimension[1]
                            for j in range(prd_num):
                                dst_position = allNodes[dst_corr[j]].position
                                dst_dimension = allNodes[dst_corr[j]].size
                                center_x += dst_position[0]+.5*dst_dimension[0]
                                center_y += dst_position[1]+.5*dst_dimension[1]
                            center_x = center_x/(rct_num + prd_num) 
                            center_y = center_y/(rct_num + prd_num)
                            center_position = [center_x, center_y]
                            handles = [center_position]
                            for j in range(rct_num):
                                src_position = allNodes[src_corr[j]].position
                                src_dimension = allNodes[src_corr[j]].size
                                src_handle_x = .5*(center_position[0] + src_position[0] + .5*src_dimension[0])
                                src_handle_y = .5*(center_position[1] + src_position[1] + .5*src_dimension[1])
                                handles.append([src_handle_x,src_handle_y])
                            for j in range(prd_num):
                                dst_position = allNodes[dst_corr[j]].position
                                dst_dimension = allNodes[dst_corr[j]].size
                                dst_handle_x = .5*(center_position[0] + dst_position[0] + .5*dst_dimension[0])
                                dst_handle_y = .5*(center_position[1] + dst_position[1] + .5*dst_dimension[1])
                                handles.append([dst_handle_x,dst_handle_y])

                            handles_Vec2 = []  
                            
                            if [] not in handles:      
                                for i in range(len(handles)):
                                    handles_Vec2.append(Vec2(handles[i][0],handles[i][1]))
                                api.update_reaction(net_index, idx, 
                                center_pos = Vec2(center_position[0],center_position[1]), 
                                handle_positions=handles_Vec2, 
                                fill_color=api.Color(reaction_line_color[0],reaction_line_color[1],reaction_line_color[2],reaction_line_color[3]))

                        except:
                            flag_add_rxn_err = 1


                        # if flag_add_rxn_err == 1:
                        #     wx.MessageBox("There are errors while loading this SBML file!", "Message", wx.OK | wx.ICON_INFORMATION)
                        
            except:
                if showDialogues:
                    wx.MessageBox("Imported SBML file is invalid.", "Message", wx.OK | wx.ICON_INFORMATION)


            # except Exception as e:
            #     raise Exception (e) 

