"""
Export the network on canvas to an SBML string as save it as a file.
Version 1.0.7: Author: Jin Xu (2023)
"""


# pylint: disable=maybe-no-member

from inspect import Parameter
import wx
from wx.core import Width
from rkviewer.plugin.classes import PluginMetadata, WindowedPlugin, PluginCategory
from rkviewer.plugin import api
from rkviewer.plugin.api import Node, Vec2, Reaction, Color, get_node_by_index
import os
from libsbml import * # does not have to import in the main.py too
import re # to process kinetic_law string
from rkviewer.config import get_theme

class ExportSBML(WindowedPlugin):
    metadata = PluginMetadata(
        name='ExportSBML',
        author='Jin Xu',
        version='1.0.7',
        short_desc='Export SBML.',
        long_desc='Export the SBML String from the network on canvas and save it to a file.',
        category=PluginCategory.MODELS
    )


    def create_window(self, dialog):
        """
        Create a window to export the SBML.
        Args:
            self
            dialog
        """
        self.window = wx.Panel(dialog, pos=(5,100), size=(300, 320))

        export_btn = wx.Button(self.window, -1, 'Export and Save', (5, 5))
        export_btn.Bind(wx.EVT_BUTTON, self.Export)

        copy_btn = wx.Button(self.window, -1, 'Copy To Clipboard', (130, 5))
        copy_btn.Bind(wx.EVT_BUTTON, self.Copy)

        #save_btn = wx.Button(self.window, -1, 'Save', (205, 5))
        #save_btn.Bind(wx.EVT_BUTTON, self.Save)

        wx.StaticText(self.window, -1, 'SBML string:', (5,30))
        self.SBMLText = wx.TextCtrl(self.window, -1, "", (10, 50), size=(260, 220), style=wx.TE_MULTILINE|wx.HSCROLL)
        self.SBMLText.SetInsertionPoint(0)

        return self.window

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


    def Export(self, evt):
        """
        Handler for the "Export and Save" button.
        Export the Network on canvas and save the SBML string to a file.
        """
        sbmlStr_layout_render = self.NetworkToSBML()
        try:
            self.SBMLText.SetValue(sbmlStr_layout_render)
            #save to local
            self.dirname=""  #set directory name to blank 
            dlg = wx.FileDialog(self.window, "Save As", self.dirname, wildcard="SBML files (*.xml)|*.xml", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
            if dlg.ShowModal() == wx.ID_OK:
                # Grab the content to be saved
                #itcontains = self.SBMLText.GetValue()
                itcontains = sbmlStr_layout_render
                # Open the file for write, write, close
                self.filename=dlg.GetFilename()
                self.dirname=dlg.GetDirectory()
                filehandle=open(os.path.join(self.dirname, self.filename),'w')
                filehandle.write(itcontains)
                filehandle.close()
            # Get rid of the dialog to keep things tidy
            dlg.Destroy()
        except:
            wx.MessageBox("No valid SBML string to export or save!", "Error")


    def NetworkToSBML(self):
        """
        Get the network on canvas and change it to an SBML string
        """

        # def getSymbols(kinetic_law):
        #     str = kinetic_law
        #     str = str.replace(' ', '')  
        #     list = re.split('[+|\-|*|/|(|)]', str)
        #     list = [i for i in list if i != '']
        #     list_update = []
        #     for i in list:
        #         x = i.split(',')
        #         list_update.extend(x)
        #     res = []
        #     [res.append(x) for x in list_update if x not in res and not x.isdigit()]
        #     return res

        
        def _cross_point(arcCenter, c2, s2):
            """
            Get the cross point of a point and a rectangle with position(top left-hand corner) and size 
            given.

            Args:  
                arcCenter:  1*2 matrix-position of the point.
                c2: 1*2 matrix-position of the rectangle (top left-hand corner).
                s2: 1*2 matrix-size of the rectangle.
            """
            pt_center = [c2[0]+.5*s2[0], c2[1]+.5*s2[1]]
            pt_up_left    = c2
            pt_up_right   = [c2[0]+s2[0], c2[1]]
            pt_down_left  = [c2[0], c2[1]+s2[1]]
            pt_down_right = [c2[0]+s2[0], c2[1]+s2[1]]

            def _line_intersection(line1, line2):
                """

                Args:  
                    line1: list of 1*2 matrix-two points to represent line1.
                    line2: list of 1*2 matrix-two points to represent line2.
                Returns:
                    [x,y]: 1*2 matrix-the point position of the crossed two lines.
                """
                xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
                ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

                def _det(a, b):
                    return a[0] * b[1] - a[1] * b[0]

                div = _det(xdiff, ydiff)
                if div == 0:
                    raise Exception('lines do not intersect1')
                d = (_det(*line1), _det(*line2))
                x = round(_det(d, xdiff) / div,2)
                y = round(_det(d, ydiff) / div,2)
                if round((x-line1[0][0])*(x-line1[1][0]),2)<=0 and round((x-line2[0][0])*(x-line2[1][0]),2)<=0 \
                and round((y-line1[0][1])*(y-line1[1][1]),2)<=0 and round((y-line2[0][1])*(y-line2[1][1]),2)<=0:
                    return [x, y]
                else:
                    raise Exception('lines do not intersect2')
            try:
                [x,y] = _line_intersection([arcCenter, pt_center], [pt_up_left, pt_down_left])
                return [x,y]
            except:
                pass

            try:
                [x,y] = _line_intersection([arcCenter, pt_center], [pt_up_left, pt_up_right])
                return [x,y]
            except:
                pass
            try:
                [x,y] = _line_intersection([arcCenter, pt_center], [pt_down_left, pt_down_right])
                return [x,y]
            except:
                pass
            try:
                [x,y] = _line_intersection([arcCenter, pt_center], [pt_up_right, pt_down_right])
                return [x,y]
            except:
                pass


        isReversible = True
        netIn = 0
        numNodes = api.node_count(netIn)
        numReactions = api.reaction_count(netIn)
        
        if numNodes == 0:
            pass
            #wx.MessageBox("There are no nodes on canvas to export.", "Message", wx.OK | wx.ICON_INFORMATION)
        else:
            allNodes = api.get_nodes(netIn)
            
            allReactions = api.get_reactions(netIn)
            allcompartments = api.get_compartments(netIn)
            #print("allNodes:", allNodes)
            #print("allReactions:", allReactions)
            #print("allcompartments:", allcompartments)
            numCompartments = len(allcompartments)      
    #######################################

            # Creates an SBMLNamespaces object with the given SBML level, version
            # package name, package version.
            # 
            # (NOTE) By default, the name of package (i.e. "layout") will be used
            # if the argument for the prefix is missing or empty. Thus the argument
            # for the prefix can be added as follows:
            # 
            #    SBMLNamespaces sbmlns(3,1,"layout",1,"LAYOUT")
            # 
            sbmlns = SBMLNamespaces(3, 1, "layout", 1)
            # create the document
            document = SBMLDocument(sbmlns)
            # set the "required" attribute of layout package  to "true"
            document.setPkgRequired("layout", False)  

            # create the Model
            model = document.createModel()
            model.setId("SBcoyote_model")
            document.setModel(model)

            # create the Compartment and species

            comp_id_list = []
            for i in range(numCompartments):
                comp_id_list.append(allcompartments[i].id) 


            if numCompartments != 0:
                if "_compartment_default_" not in comp_id_list:
                    compartment = model.createCompartment()
                    comp_id="_compartment_default_"
                    compartment.setId(comp_id)
                    compartment.setConstant(True)
                    compartment.setVolume(1.)
                
                for i in range(numCompartments):   
                    compartment = model.createCompartment()
                    comp_id=allcompartments[i].id
                    compartment.setId(comp_id)
                    compartment.setConstant(True)
                    compartment.setVolume(1.)
                spec_id_list = []
                for i in range(numNodes):
                    original_index = allNodes[i].original_index
                    if original_index == -1:
                        spec_id = allNodes[i].id
                        spec_name = allNodes[i].node_name
                        spec_SBO = allNodes[i].node_SBO
                        if ' ' in spec_id:
                            spec_id = spec_id.replace(' ', '_')
                        if spec_id not in spec_id_list:
                            spec_id_list.append(spec_id)
                        species = model.createSpecies()
                        species.setId(spec_id)
                        species.setName(spec_name)
                        species.setSBOTerm(spec_SBO)
                        comp_idx = allNodes[i].comp_idx
                        if comp_idx != -1:
                            comp_id = allcompartments[comp_idx].id 
                            species.setCompartment(comp_id)  
                        else:
                            species.setCompartment("_compartment_default_") #why "_compartment_default_"
                        species.setInitialConcentration(allNodes[i].concentration)	
                        species.setHasOnlySubstanceUnits(False)
                        species.setBoundaryCondition(False)
                        species.setConstant(False)             
                        if allNodes[i].floating_node == False:
                            species.setBoundaryCondition(True)
                            species.setConstant(True)   
            else: #set default compartment
                compartment = model.createCompartment()
                comp_id="_compartment_default_"
                compartment.setId(comp_id)
                compartment.setConstant(True)
                compartment.setVolume(1.)
                spec_id_list = []
                for i in range(numNodes):
                    original_index = allNodes[i].original_index
                    if original_index == -1:
                        spec_id = allNodes[i].id
                        spec_name = allNodes[i].node_name
                        spec_SBO = allNodes[i].node_SBO
                        if ' ' in spec_id:
                            spec_id = spec_id.replace(' ', '_')
                        if spec_id not in spec_id_list:
                            spec_id_list.append(spec_id)
                        species = model.createSpecies()
                        species.setId(spec_id)
                        species.setName(spec_name)
                        species.setSBOTerm(spec_SBO) 
                        species.setCompartment(comp_id) #why "_compartment_default_"
                        species.setInitialConcentration(allNodes[i].concentration)	
                        species.setHasOnlySubstanceUnits(False)
                        species.setBoundaryCondition(False)
                        species.setConstant(False)             
                        if allNodes[i].floating_node == False:
                            species.setBoundaryCondition(True)
                            species.setConstant(True)
            # create reactions:
            parameter_id_value_dict_self_pre = {}  
            
            for i in range(numReactions):
                reaction_id = allReactions[i].id
                rct = [] # id list of the rcts
                prd = []
                mod = []
                rct_num = len(allReactions[i].sources)
                prd_num = len(allReactions[i].targets)
                mod_num = len(allReactions[i].modifiers)
                for j in range(rct_num):
                    temp_spec_id = get_node_by_index(netIn, allReactions[i].sources[j]).id
                    if ' ' in temp_spec_id:
                        temp_spec_id = temp_spec_id.replace(' ', '_')
                    rct.append(temp_spec_id)
                for j in range(prd_num):
                    temp_spec_id = get_node_by_index(netIn, allReactions[i].targets[j]).id
                    if ' ' in temp_spec_id:
                        temp_spec_id = temp_spec_id.replace(' ', '_')
                    prd.append(temp_spec_id)
                for j in range(mod_num):
                    temp_spec_id = get_node_by_index(netIn, list(allReactions[i].modifiers)[j]).id
                    if ' ' in temp_spec_id:
                        temp_spec_id = temp_spec_id.replace(' ', '_')
                    mod.append(temp_spec_id)

                kinetic_law_from_user = allReactions[i].rate_law
                
                if kinetic_law_from_user == '':
                    kinetic_law = ''
                    kinetic_law = kinetic_law + 'E' + str (i) + '*(k' + str (i) 
                    parameter_id_value_dict_self_pre['E' + str(i)] = 0.1
                    parameter_id_value_dict_self_pre['k' + str(i)] = 0.1

                    for j in range(rct_num):
                        kinetic_law = kinetic_law + '*' + rct[j]
                        
                    if isReversible:
                        kinetic_law = kinetic_law + ' - k' + str (i) + 'r'
                        parameter_id_value_dict_self_pre['k' + str (i) + 'r'] = 0.1
                        for j in range(prd_num):
                            kinetic_law = kinetic_law + '*' + prd[j]
                    kinetic_law = kinetic_law + ')'
                else:
                    kinetic_law = kinetic_law_from_user

                reaction = model.createReaction()
                reaction.setId(allReactions[i].id)
                reaction.setReversible(False)
                reaction.setFast(False)
                if isReversible:
                    reaction.setReversible(True)
                
                kinetics = reaction.createKineticLaw()
                kinetics.setFormula(kinetic_law)
                
                for j in range(rct_num):
                    reference = reaction.createReactant()
                    reference.setSpecies(rct[j])
                    ref_id = "SpecRef_" + reaction_id + "_rct" + str(j)
                    reference.setId(ref_id)
                    #reference.setStoichiometry(1.)
                    reference.setConstant(False)

                for j in range(prd_num):
                    reference = reaction.createProduct()
                    reference.setSpecies(prd[j])
                    ref_id = "SpecRef_" + reaction_id + "_prd" + str(j)
                    reference.setId(ref_id)
                    #reference.setStoichiometry(1.)
                    reference.setConstant(False)

                for j in range(mod_num):
                    reference = reaction.createModifier()
                    reference.setSpecies(mod[j])
                    ref_id = "SpecRef_" + reaction_id + "_mod" + str(j)
                    reference.setId(ref_id)

            parameter_id_value_dict = api.get_parameters(netIn)
            parameter_id_value_dict.update(parameter_id_value_dict_self_pre)
            for name,dict_ in parameter_id_value_dict.items():
                parameters = model.createParameter()
                parameters.setId(name)
                parameters.setValue(dict_)
                parameters.setConstant(True)
            
            # create the Layout

            #
            # set the LayoutPkgNamespaces for Level 3 Version1 Layout Version 1
            #
            layoutns = LayoutPkgNamespaces(3, 1, 1)

            renderns = RenderPkgNamespaces(3, 1, 1)

            #
            # Get a LayoutModelPlugin object plugged in the model object.
            #
            # The type of the returned value of SBase::getPlugin() function is SBasePlugin, and
            # thus the value needs to be casted for the corresponding derived class.
            #

            mplugin = model.getPlugin("layout")

            # rPlugin = model.getPlugin("render")
            # if rPlugin is None:
            #   print("there is no render outside layout.")
                    
            # lolPlugin = mplugin.getListOfLayouts().getPlugin("render")
            # if lolPlugin is None:
            #   print("there is no render info inside layout.")
            
            if mplugin is None:
                # print(
                #     "[Fatal Error] Layout Extension Level " + layoutns.getLevel() + " Version " + layoutns.getVersion() + " package version " + layoutns.getPackageVersion() + " is not registered.")
                # sys.exit(1)
                wx.MessageBox("There is no layout information.", "Message", wx.OK | wx.ICON_INFORMATION)


            #
            # Creates a Layout object via LayoutModelPlugin object.
            #
            layout = mplugin.createLayout()
            layout.setId("SBcoyote_layout")
            def_canvas_width = get_theme('real_canvas_width')
            def_canvas_height = get_theme('real_canvas_height')
            #layout_width = 10000 - 20
            #layout_height = 6200 - 20
            layout_width = def_canvas_width - 20.
            layout_height = def_canvas_height - 20.
            layout.setDimensions(Dimensions(layoutns, layout_width, layout_height))
            # random network (40+800x, 40+800y)

            #create the CompartmentGlyph and SpeciesGlyphs
            if numCompartments != 0:
                for i in range(numCompartments):   
                    comp_id=allcompartments[i].id
                    if comp_id != "_compartment_default_":
                        compartmentGlyph = layout.createCompartmentGlyph()
                        compG_id = "CompG_" + comp_id
                        compartmentGlyph.setId(compG_id)
                        compartmentGlyph.setCompartmentId(comp_id)
                        bb_id  = "bb_" + comp_id
                        pos_x  = allcompartments[i].position.x
                        pos_y  = allcompartments[i].position.y
                        width  = allcompartments[i].size.x
                        height = allcompartments[i].size.y
                        compartmentGlyph.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x, pos_y, width, height))
                for i in range(numNodes):   
                    spec_id = allNodes[i].id
                    if ' ' in spec_id:
                        spec_id = spec_id.replace(' ', '_')
                    spec_index = allNodes[i].index
                    # spec_shapeIdx = allNodes[i].shape_index
                    primitive, _ = allNodes[i].shape.text_item
                    alignment_value = primitive.alignment.value
                    position_value = primitive.position.value
                    speciesGlyph = layout.createSpeciesGlyph()
                    specG_id = "SpecG_"  + spec_id + '_idx_' + str(spec_index)
                    speciesGlyph.setId(specG_id)
                    speciesGlyph.setSpeciesId(spec_id)
                    bb_id  = "bb_" + spec_id + '_idx_' + str(spec_index)
                    pos_x  = allNodes[i].position.x
                    pos_y  = allNodes[i].position.y
                    width  = allNodes[i].size.x
                    height = allNodes[i].size.y
                    speciesGlyph.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x, pos_y, width, height))

                    textGlyph = layout.createTextGlyph()
                    textG_id = "TextG_" + spec_id + '_idx_' + str(spec_index)
                    textGlyph.setId(textG_id)
                    textGlyph.setText(spec_id)
                    bb_id  = "bb_spec_text_" + spec_id + '_idx_' + str(spec_index)
                    # if spec_shapeIdx == 6: #rough by eyes
                    #     pos_x_text = pos_x + 50
                    #     pos_y_text = pos_y + 30
                    # else:
                    pos_x_text = pos_x
                    pos_y_text = pos_y
                    #rough position, if text is outside the node
                    if position_value != 1: #not inside the node
                        if alignment_value == 1: #LEFT
                            pos_x_text = pos_x - width 
                        if alignment_value == 3: #RIGHT
                            pos_x_text = pos_x + width                           
                    if position_value == 2: #ABOVE
                        pos_y_text = pos_y - height
                    if position_value == 3: #BELOW
                        pos_y_text = pos_y + height 
                    textGlyph.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x_text, pos_y_text, width, height))
                    #textGlyph.setOriginOfTextId(specG_id)
                    textGlyph.setGraphicalObjectId(specG_id)
            else:#there is no compartment  
                comp_id= "_compartment_default_"
                compartmentGlyph = layout.createCompartmentGlyph()
                compG_id = "CompG_" + comp_id
                compartmentGlyph.setId(compG_id)
                compartmentGlyph.setCompartmentId(comp_id)
                bb_id  = "bb_" + comp_id
                pos_x  = 10
                pos_y  = 10
                width  = layout_width
                height = layout_height
                compartmentGlyph.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x, pos_y, width, height))
            
                for i in range(numNodes):
                    spec_id = allNodes[i].id
                    if ' ' in spec_id:
                        spec_id = spec_id.replace(' ', '_')
                    spec_index = allNodes[i].index
                    #spec_shapeIdx = allNodes[i].shape_index
                    primitive, _ = allNodes[i].shape.text_item
                    alignment_value = primitive.alignment.value
                    position_value = primitive.position.value
                    speciesGlyph = layout.createSpeciesGlyph()
                    specG_id = "SpecG_"  + spec_id + '_idx_' + str(spec_index)
                    speciesGlyph.setId(specG_id)
                    speciesGlyph.setSpeciesId(spec_id)
                    bb_id  = "bb_" + spec_id + '_idx_' + str(spec_index)
                    pos_x  = allNodes[i].position.x
                    pos_y  = allNodes[i].position.y
                    width  = allNodes[i].size.x
                    height = allNodes[i].size.y
                    speciesGlyph.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x, pos_y, width, height))

                    textGlyph = layout.createTextGlyph()
                    textG_id = "TextG_" + spec_id + '_idx_' + str(spec_index)
                    textGlyph.setId(textG_id)
                    textGlyph.setText(spec_id)
                    # if spec_shapeIdx == 6: #rough by eyes
                    #     pos_x_text = pos_x + 50
                    #     pos_y_text = pos_y + 30
                    # else:
                    pos_x_text = pos_x
                    pos_y_text = pos_y
                    #rough position, if text is outside the node
                    if position_value != 1: #not inside the node
                        if alignment_value == 1: #LEFT
                            pos_x_text = pos_x - width 
                        if alignment_value == 3: #RIGHT
                            pos_x_text = pos_x + width                           
                    if position_value == 2: #ABOVE
                        pos_y_text = pos_y - height
                    if position_value == 3: #BELOW
                        pos_y_text = pos_y + height
                    bb_id  = "bb_spec_text_" + spec_id + '_idx_' + str(spec_index)
                    textGlyph.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x_text, pos_y_text, width, height))
                    #textGlyph.setOriginOfTextId(specG_id)
                    textGlyph.setGraphicalObjectId(specG_id)

            # create the ReactionGlyphs and SpeciesReferenceGlyphs
            for i in range(numReactions):
                if allReactions[i].using_bezier == True:
                    reaction_id = allReactions[i].id
                    center_pos = allReactions[i].center_pos
                    centroid = api.compute_centroid(netIn, allReactions[i].sources, allReactions[i].targets)
                    try:
                        center_value = [center_pos.x,center_pos.y]
                    except:
                        center_value = [centroid.x,centroid.y]
                    
                    reactionGlyph = layout.createReactionGlyph()
                    reactionG_id = "ReactionG_" + reaction_id
                    reactionGlyph.setId(reactionG_id)
                    reactionGlyph.setReactionId(reaction_id)

                    reaction_line_thickness = allReactions[i].line_thickness
                    
                    reactionCurve = reactionGlyph.getCurve()
                    ls = reactionCurve.createLineSegment()
                    ls.setStart(Point(layoutns, center_value[0], center_value[1]))
                    ls.setEnd(Point(layoutns, center_value[0], center_value[1]))

                    rct = [] # id list of the rcts
                    prd = []
                    mod = []
                    rct_index = []
                    prd_index = []
                    mod_index = []
                    rct_num = len(allReactions[i].sources)
                    prd_num = len(allReactions[i].targets)
                    mod_num = len(allReactions[i].modifiers)

                    for j in range(rct_num):
                        temp_spec_id = get_node_by_index(netIn, allReactions[i].sources[j]).id
                        if ' ' in temp_spec_id:
                            temp_spec_id = temp_spec_id.replace(' ', '_')
                        rct.append(temp_spec_id)
                        rct_index.append(get_node_by_index(netIn, allReactions[i].sources[j]).index)
                    for j in range(prd_num):
                        temp_spec_id = get_node_by_index(netIn, allReactions[i].targets[j]).id
                        if ' ' in temp_spec_id:
                            temp_spec_id = temp_spec_id.replace(' ', '_')
                        prd.append(temp_spec_id)
                        prd_index.append(get_node_by_index(netIn, allReactions[i].targets[j]).index)
                    for j in range(mod_num):
                        temp_spec_id = get_node_by_index(netIn, list(allReactions[i].modifiers)[j]).id
                        if ' ' in temp_spec_id:
                            temp_spec_id = temp_spec_id.replace(' ', '_')
                        mod.append(temp_spec_id)
                        mod_index.append(get_node_by_index(netIn, list(allReactions[i].modifiers)[j]).index)

                    
                    for j in range(rct_num):
                        ref_id = "SpecRef_" + reaction_id + "_rct" + str(j)

                        speciesReferenceGlyph = reactionGlyph.createSpeciesReferenceGlyph()
                        specsRefG_id = "SpecRefG_" + reaction_id + "_rct" + str(j)
                        specG_id = "SpecG_" + rct[j] + '_idx_' + str(rct_index[j])
                        speciesReferenceGlyph.setId(specsRefG_id)
                        speciesReferenceGlyph.setSpeciesGlyphId(specG_id)
                        speciesReferenceGlyph.setSpeciesReferenceId(ref_id)
                        speciesReferenceGlyph.setRole(SPECIES_ROLE_SUBSTRATE)
                        speciesReferenceCurve = speciesReferenceGlyph.getCurve()
                        cb = speciesReferenceCurve.createCubicBezier()

                        handle1 = api.get_reaction_center_handle(netIn, allReactions[i].index)
                        handle2 = api.get_reaction_node_handle(netIn, allReactions[i].index,
                            allReactions[i].sources[j],is_source=True)

                        pos_x = get_node_by_index(netIn,allReactions[i].sources[j]).position.x
                        pos_y = get_node_by_index(netIn,allReactions[i].sources[j]).position.y
                        width = get_node_by_index(netIn,allReactions[i].sources[j]).size.x
                        height = get_node_by_index(netIn,allReactions[i].sources[j]).size.y
                        
              
                        line_end_pt = _cross_point(handle2, 
                        [pos_x-reaction_line_thickness, pos_y-reaction_line_thickness], 
                        [width+2.*reaction_line_thickness,height+2.*reaction_line_thickness])
                        if line_end_pt == None:
                            line_end_pt = _cross_point(center_value, 
                            [pos_x-reaction_line_thickness, pos_y-reaction_line_thickness], 
                            [width+2.*reaction_line_thickness,height+2.*reaction_line_thickness])
                        try:
                            cb.setStart(Point(layoutns, line_end_pt[0], line_end_pt[1]))
                        except:     
                            cb.setStart(Point(layoutns, pos_x + 0.5*width, pos_y + 0.5*height))
                        cb.setBasePoint1(Point(layoutns, handle2.x, handle2.y))
                        cb.setBasePoint2(Point(layoutns, handle1.x, handle1.y))
                        cb.setEnd(Point(layoutns, center_value[0], center_value[1]))
                        
                    for j in range(prd_num):
                        ref_id = "SpecRef_" + reaction_id + "_prd" + str(j)
                        speciesReferenceGlyph = reactionGlyph.createSpeciesReferenceGlyph()
                        specsRefG_id = "SpecRefG_" + reaction_id + "_prd" + str(j)
                        specG_id = "SpecG_" + prd[j]  + '_idx_' + str(prd_index[j])
                        speciesReferenceGlyph.setId(specsRefG_id)
                        speciesReferenceGlyph.setSpeciesGlyphId(specG_id)
                        speciesReferenceGlyph.setSpeciesReferenceId(ref_id)
                        speciesReferenceGlyph.setRole(SPECIES_ROLE_PRODUCT)

                        speciesReferenceCurve = speciesReferenceGlyph.getCurve()
                        cb = speciesReferenceCurve.createCubicBezier()
                        cb.setStart(Point(layoutns, center_value[0], center_value[1]))

                        handle_center = api.get_reaction_center_handle(netIn, allReactions[i].index)
                        handle1 = [2.*center_value[0]-handle_center.x, 2.*center_value[1]-handle_center.y]
                        
                        handle2 = api.get_reaction_node_handle(netIn, allReactions[i].index,
                            allReactions[i].targets[j],is_source=False)
                        cb.setBasePoint1(Point(layoutns, handle1[0], handle1[1]))
                        cb.setBasePoint2(Point(layoutns, handle2.x, handle2.y))

                        pos_x = get_node_by_index(netIn, allReactions[i].targets[j]).position.x
                        pos_y = get_node_by_index(netIn, allReactions[i].targets[j]).position.y
                        width = get_node_by_index(netIn, allReactions[i].targets[j]).size.x
                        height = get_node_by_index(netIn, allReactions[i].targets[j]).size.y
                        
                        line_head_pt = _cross_point(handle2, 
                        [pos_x-reaction_line_thickness, pos_y-reaction_line_thickness], 
                        [width+2.*reaction_line_thickness,height+2.*reaction_line_thickness])
                        if line_head_pt == None:
                            line_head_pt = _cross_point(center_value, 
                            [pos_x-reaction_line_thickness, pos_y-reaction_line_thickness], 
                            [width+2.*reaction_line_thickness,height+2.*reaction_line_thickness])
                    
                        try:
                            cb.setEnd(Point(layoutns, line_head_pt[0], line_head_pt[1]))
                        except:
                            cb.setEnd(Point(layoutns, pos_x + 0.5*width, pos_y + 0.5*height))

                    for j in range(mod_num):
                        ref_id = "SpecRef_" + reaction_id + "_mod" + str(j)
                        speciesReferenceGlyph = reactionGlyph.createSpeciesReferenceGlyph()
                        specsRefG_id = "SpecRefG_" + reaction_id + "_mod" + str(j)
                        specG_id = "SpecG_" + mod[j]  + '_idx_' + str(mod_index[j])
                        speciesReferenceGlyph.setId(specsRefG_id)
                        speciesReferenceGlyph.setSpeciesGlyphId(specG_id)
                        speciesReferenceGlyph.setSpeciesReferenceId(ref_id)
                        speciesReferenceGlyph.setRole(SPECIES_ROLE_MODIFIER)

                        speciesReferenceCurve = speciesReferenceGlyph.getCurve()
                        mod_ls = speciesReferenceCurve.createLineSegment()

                        pos_x = get_node_by_index(netIn, list(allReactions[i].modifiers)[j]).position.x
                        pos_y = get_node_by_index(netIn, list(allReactions[i].modifiers)[j]).position.y
                        width = get_node_by_index(netIn, list(allReactions[i].modifiers)[j]).size.x
                        height = get_node_by_index(netIn, list(allReactions[i].modifiers)[j]).size.y

                        mod_start_virtual_x = pos_x + 0.5*width 
                        mod_start_virtual_y = pos_y + 0.5*height
                        try: 
                            [mod_start_x, mod_start_y] = _cross_point(center_value, 
                            [pos_x-reaction_line_thickness*2.,pos_y-reaction_line_thickness*2.],
                            [width+reaction_line_thickness*4., height+reaction_line_thickness*4.]) 
                        except: 
                            mod_start_x = mod_start_virtual_x
                            mod_start_y = mod_start_virtual_y
                        mod_ls.setStart(Point(layoutns, mod_start_x, mod_start_y))

    
                        try: 
                            [mod_end_x, mod_end_y] = _cross_point([mod_start_virtual_x, mod_start_virtual_y],
                            [center_value[0]-5.*reaction_line_thickness, center_value[1]-5.*reaction_line_thickness], 
                            [10.*reaction_line_thickness, 10.*reaction_line_thickness])
                        except: 
                            [mod_end_x, mod_end_y] = center_value
                        try:
                            mod_ls.setEnd(Point(layoutns, mod_end_x, mod_end_y))
                        except:
                            mod_ls.setEnd(Point(layoutns, center_value[0], center_value[1]))
            

                else:
                    reaction_id = allReactions[i].id
                    center_pos = allReactions[i].center_pos
                    centroid = api.compute_centroid(netIn, allReactions[i].sources, allReactions[i].targets)
                    handles = api.default_handle_positions(netIn,i)

                    try:
                        center_value = [center_pos.x,center_pos.y]
                    except:
                        center_value = [centroid.x,centroid.y]

                    
                    reactionGlyph = layout.createReactionGlyph()
                    reactionG_id = "ReactionG_" + reaction_id
                    reactionGlyph.setId(reactionG_id)
                    reactionGlyph.setReactionId(reaction_id)
                    
                    reactionCurve = reactionGlyph.getCurve()
                    ls = reactionCurve.createLineSegment()
                    ls.setStart(Point(layoutns, center_value[0], center_value[1]))
                    ls.setEnd(Point(layoutns, center_value[0], center_value[1]))

                    rct = [] # id list of the rcts
                    prd = []
                    mod = []
                    rct_index = []
                    prd_index = []
                    mod_index = []
                    rct_num = len(allReactions[i].sources)
                    prd_num = len(allReactions[i].targets)
                    mod_num = len(allReactions[i].modifiers)

                    # for j in range(rct_num):
                    #     rct.append(get_node_by_index(netIn, allReactions[i].sources[j]).id)
                    #     rct_index.append(get_node_by_index(netIn, allReactions[i].sources[j]).index)
                    # for j in range(prd_num):
                    #     prd.append(get_node_by_index(netIn, allReactions[i].targets[j]).id)
                    #     prd_index.append(get_node_by_index(netIn, allReactions[i].targets[j]).index)
                    # for j in range(mod_num):
                    #     mod.append(get_node_by_index(netIn, list(allReactions[i].modifiers)[j]).id)
                    #     mod_index.append(get_node_by_index(netIn, list(allReactions[i].modifiers)[j]).index)
                    
                    for j in range(rct_num):
                        temp_spec_id = get_node_by_index(netIn, allReactions[i].sources[j]).id
                        if ' ' in temp_spec_id:
                            temp_spec_id = temp_spec_id.replace(' ', '_')
                        rct.append(temp_spec_id)
                        rct_index.append(get_node_by_index(netIn, allReactions[i].sources[j]).index)
                    for j in range(prd_num):
                        temp_spec_id = get_node_by_index(netIn, allReactions[i].targets[j]).id
                        if ' ' in temp_spec_id:
                            temp_spec_id = temp_spec_id.replace(' ', '_')
                        prd.append(temp_spec_id)
                        prd_index.append(get_node_by_index(netIn, allReactions[i].targets[j]).index)
                    for j in range(mod_num):
                        temp_spec_id = get_node_by_index(netIn, list(allReactions[i].modifiers)[j]).id
                        if ' ' in temp_spec_id:
                            temp_spec_id = temp_spec_id.replace(' ', '_')
                        mod.append(temp_spec_id)
                        mod_index.append(get_node_by_index(netIn, list(allReactions[i].modifiers)[j]).index)


                    for j in range(rct_num):
                        ref_id = "SpecRef_" + reaction_id + "_rct" + str(j)

                        speciesReferenceGlyph = reactionGlyph.createSpeciesReferenceGlyph()
                        specsRefG_id = "SpecRefG_" + reaction_id + "_rct" + str(j)
                        specG_id = "SpecG_" + rct[j] + '_idx_' + str(rct_index[j])
                        speciesReferenceGlyph.setId(specsRefG_id)
                        speciesReferenceGlyph.setSpeciesGlyphId(specG_id)
                        speciesReferenceGlyph.setSpeciesReferenceId(ref_id)
                        speciesReferenceGlyph.setRole(SPECIES_ROLE_SUBSTRATE)
                        speciesReferenceCurve = speciesReferenceGlyph.getCurve()
                        cb = speciesReferenceCurve.createCubicBezier()
                        # handle1 = api.get_reaction_center_handle(netIn, allReactions[i].index)
                        # handle2 = api.get_reaction_node_handle(netIn, allReactions[i].index,
                        #     allReactions[i].sources[j],is_source=True)
                        handle1 = handles[0]
                        handle2 = handles[1+j]
                        
                        pos_x = get_node_by_index(netIn,allReactions[i].sources[j]).position.x
                        pos_y = get_node_by_index(netIn,allReactions[i].sources[j]).position.y
                        width = get_node_by_index(netIn,allReactions[i].sources[j]).size.x
                        height = get_node_by_index(netIn,allReactions[i].sources[j]).size.y

                        line_end_pt = _cross_point(handle2, 
                        [pos_x-reaction_line_thickness, pos_y-reaction_line_thickness], 
                        [width+2.*reaction_line_thickness,height+2.*reaction_line_thickness])
                        if line_end_pt == None:
                            line_end_pt = _cross_point(center_value, 
                            [pos_x-reaction_line_thickness, pos_y-reaction_line_thickness], 
                            [width+2.*reaction_line_thickness,height+2.*reaction_line_thickness])
                        try:
                            cb.setStart(Point(layoutns, line_end_pt[0], line_end_pt[1]))
                        except:     
                            cb.setStart(Point(layoutns, pos_x + 0.5*width, pos_y + 0.5*height))

                        cb.setBasePoint1(Point(layoutns, handle2.x, handle2.y))
                        cb.setBasePoint2(Point(layoutns, handle1.x, handle1.y))
                        cb.setEnd(Point(layoutns, center_value[0], center_value[1]))

                    for j in range(prd_num):
                        ref_id = "SpecRef_" + reaction_id + "_prd" + str(j)
                        speciesReferenceGlyph = reactionGlyph.createSpeciesReferenceGlyph()
                        specsRefG_id = "SpecRefG_" + reaction_id + "_prd" + str(j)
                        specG_id = "SpecG_" + prd[j]  + '_idx_' + str(prd_index[j])
                        speciesReferenceGlyph.setId(specsRefG_id)
                        speciesReferenceGlyph.setSpeciesGlyphId(specG_id)
                        speciesReferenceGlyph.setSpeciesReferenceId(ref_id)
                        speciesReferenceGlyph.setRole(SPECIES_ROLE_PRODUCT)

                        speciesReferenceCurve = speciesReferenceGlyph.getCurve()
                        cb = speciesReferenceCurve.createCubicBezier()
                        cb.setStart(Point(layoutns, center_value[0], center_value[1]))

                        # handle1 = api.get_reaction_center_handle(netIn, allReactions[i].index)
                        # handle2 = api.get_reaction_node_handle(netIn, allReactions[i].index,
                        #     allReactions[i].targets[j],is_source=False)

                        handle1 = [2.*center_value[0]-handles[0].x, 2.*center_value[1]-handles[0].y]
                        handle2 = handles[1+rct_num+j]
                        cb.setBasePoint1(Point(layoutns, handle1[0], handle1[1]))
                        cb.setBasePoint2(Point(layoutns, handle2.x, handle2.y))

                        pos_x = get_node_by_index(netIn, allReactions[i].targets[j]).position.x
                        pos_y = get_node_by_index(netIn, allReactions[i].targets[j]).position.y
                        width = get_node_by_index(netIn, allReactions[i].targets[j]).size.x
                        height = get_node_by_index(netIn, allReactions[i].targets[j]).size.y

                        line_head_pt = _cross_point(handle2, 
                        [pos_x-reaction_line_thickness, pos_y-reaction_line_thickness], 
                        [width+2.*reaction_line_thickness,height+2.*reaction_line_thickness])
                        if line_head_pt == None:
                            line_head_pt = _cross_point(center_value, 
                            [pos_x-reaction_line_thickness, pos_y-reaction_line_thickness], 
                            [width+2.*reaction_line_thickness,height+2.*reaction_line_thickness])                   
                        try:
                            cb.setEnd(Point(layoutns, line_head_pt[0], line_head_pt[1]))
                        except:
                            cb.setEnd(Point(layoutns, pos_x + 0.5*width, pos_y + 0.5*height))

                    for j in range(mod_num):
                        ref_id = "SpecRef_" + reaction_id + "_mod" + str(j)
                        speciesReferenceGlyph = reactionGlyph.createSpeciesReferenceGlyph()
                        specsRefG_id = "SpecRefG_" + reaction_id + "_mod" + str(j)
                        specG_id = "SpecG_" + mod[j]  + '_idx_' + str(mod_index[j])
                        speciesReferenceGlyph.setId(specsRefG_id)
                        speciesReferenceGlyph.setSpeciesGlyphId(specG_id)
                        speciesReferenceGlyph.setSpeciesReferenceId(ref_id)
                        speciesReferenceGlyph.setRole(SPECIES_ROLE_MODIFIER)

                        speciesReferenceCurve = speciesReferenceGlyph.getCurve()
                        mod_ls = speciesReferenceCurve.createLineSegment()

                        pos_x = get_node_by_index(netIn, list(allReactions[i].modifiers)[j]).position.x
                        pos_y = get_node_by_index(netIn, list(allReactions[i].modifiers)[j]).position.y
                        width = get_node_by_index(netIn, list(allReactions[i].modifiers)[j]).size.x
                        height = get_node_by_index(netIn, list(allReactions[i].modifiers)[j]).size.y

                        mod_start_virtual_x = pos_x + 0.5*width 
                        mod_start_virtual_y = pos_y + 0.5*height
                        try: 
                            [mod_start_x, mod_start_y] = _cross_point(center_value, 
                            [pos_x-reaction_line_thickness*2.,pos_y-reaction_line_thickness*2.],
                            [width+reaction_line_thickness*4., height+reaction_line_thickness*4.]) 
                        except: 
                            mod_start_x = mod_start_virtual_x
                            mod_start_y = mod_start_virtual_y
                        mod_ls.setStart(Point(layoutns, mod_start_x, mod_start_y))

    
                        try: 
                            [mod_end_x, mod_end_y] = _cross_point([mod_start_virtual_x, mod_start_virtual_y],
                            [center_value[0]-5.*reaction_line_thickness, center_value[1]-5.*reaction_line_thickness], 
                            [10.*reaction_line_thickness, 10.*reaction_line_thickness])
                        except: 
                            [mod_end_x, mod_end_y] = center_value
                        try:
                            mod_ls.setEnd(Point(layoutns, mod_end_x, mod_end_y))
                        except:
                            mod_ls.setEnd(Point(layoutns, center_value[0], center_value[1]))
            

            sbmlStr_layout = writeSBMLToString(document) #sbmlStr is w/o layout info 

            doc = readSBMLFromString(sbmlStr_layout)
            model_layout = doc.getModel()
            mplugin = model_layout.getPlugin("layout")

            # add render information to the first layout
            layout = mplugin.getLayout(0)

            rPlugin = layout.getPlugin("render")

            uri = RenderExtension.getXmlnsL2() if doc.getLevel() == 2 else RenderExtension.getXmlnsL3V1V1();

            # enable render package
            doc.enablePackage(uri, "render", True)
            doc.setPackageRequired("render", False)

            rPlugin = layout.getPlugin("render")

            rInfo = rPlugin.createLocalRenderInformation()
            rInfo.setId("info")
            rInfo.setName("Render Information")
            rInfo.setProgramName("RenderInformation")
            rInfo.setProgramVersion("1.0")

            default_modifier_color_str = '#%02x%02x%02x%02x' % (208,134,249, 255)
            color = rInfo.createColorDefinition()
            color.setId("_default_modifier_color_")
            color.setColorValue(default_modifier_color_str)


            if numCompartments != 0:  
                for i in range(len(allcompartments)):
                    comp_id = allcompartments[i].id
                    compG_id = "CompG_" + comp_id
                    if comp_id != '_compartment_default':
                        fill_color        = allcompartments[i].fill_color
                        border_color      = allcompartments[i].border_color
                        comp_border_width = allcompartments[i].border_width
                        fill_color_str    = '#%02x%02x%02x%02x' % (fill_color.r,fill_color.g,fill_color.b,fill_color.a)
                        border_color_str  = '#%02x%02x%02x%02x' % (border_color.r,border_color.g,border_color.b,border_color.a)

                        color = rInfo.createColorDefinition()
                        color.setId("comp_fill_color" + "_" + comp_id)
                        color.setColorValue(fill_color_str)

                        color = rInfo.createColorDefinition()
                        color.setId("comp_border_color" + "_" + comp_id)
                        color.setColorValue(border_color_str)

                        # add a list of styles 
                        style = rInfo.createStyle("compStyle" + "_" + comp_id)
                        style.getGroup().setFillColor("comp_fill_color" + "_" + comp_id)
                        style.getGroup().setStroke("comp_border_color" + "_" + comp_id)
                        style.getGroup().setStrokeWidth(comp_border_width)
                        style.addType("COMPARTMENTGLYPH")
                        style.addId(compG_id)
                        #style.addId(comp_id)
                        rectangle = style.getGroup().createRectangle()
                        rectangle.setCoordinatesAndSize(RelAbsVector(0,0),RelAbsVector(0,0),RelAbsVector(0,0),RelAbsVector(0,100),RelAbsVector(0,100))

            else:
                comp_id = '_compartment_default'
                compG_id = "CompG_" + comp_id
                comp_border_width = 2.
                #set default compartment with white color
                fill_color_str = '#ffffffff'
                border_color_str = '#ffffffff'

                color = rInfo.createColorDefinition()
                color.setId("comp_fill_color")
                color.setColorValue(fill_color_str)

                color = rInfo.createColorDefinition()
                color.setId("comp_border_color")
                color.setColorValue(border_color_str)

                # add a list of styles 
                style = rInfo.createStyle("compStyle")
                style.getGroup().setFillColor("comp_fill_color")
                style.getGroup().setStroke("comp_border_color")
                style.getGroup().setStrokeWidth(comp_border_width)
                style.addType("COMPARTMENTGLYPH")
                style.addId(compG_id)
                #style.addId(comp_id)
                rectangle = style.getGroup().createRectangle()
                rectangle.setCoordinatesAndSize(RelAbsVector(0,0),RelAbsVector(0,0),RelAbsVector(0,0),RelAbsVector(0,100),RelAbsVector(0,100))

            for i in range(len(allNodes)):
                node =  allNodes[i]
                spec_id = node.id
                if ' ' in spec_id:
                    spec_id = spec_id.replace(' ', '_')
                spec_index = node.index
                specG_id = "SpecG_"  + spec_id + '_idx_' + str(spec_index)
                textG_id = "TextG_" + spec_id + '_idx_' + str(spec_index)
                #print("id:", spec_id)
                #print("shape_index", node.shape)
                try: 
                    primitive, _ = node.shape.items[0]
                    spec_fill_color   = primitive.fill_color
                    spec_border_color = primitive.border_color
                    spec_fill_color_str   = '#%02x%02x%02x%02x' % (spec_fill_color.r,spec_fill_color.g,spec_fill_color.b,spec_fill_color.a)
                    spec_border_color_str = '#%02x%02x%02x%02x' % (spec_border_color.r,spec_border_color.g,spec_border_color.b,spec_border_color.a)
                    spec_border_width = primitive.border_width
                    primitive, _ = node.shape.text_item
                    text_font_size = primitive.font_size
                    font_color = primitive.font_color
                    text_line_color_str =  '#%02x%02x%02x%02x' % (font_color.r,font_color.g,font_color.b,font_color.a)

                except:#text-only
                    #set default species/node with white color
                    spec_fill_color_str = '#ffffffff'
                    spec_border_color_str = '#ffffffff'
                    spec_border_width = 2.
                    text_line_color_str = '#000000ff'
                    text_line_width = 1.
                    text_font_size = 12.
                    text_font_family = ""
                    [text_anchor, text_vanchor] = ['middle', 'middle']



                color = rInfo.createColorDefinition()
                color.setId("spec_fill_color" + "_" + spec_id)
                color.setColorValue(spec_fill_color_str)

                color = rInfo.createColorDefinition()
                color.setId("spec_border_color" + "_" + spec_id)
                color.setColorValue(spec_border_color_str)

                color = rInfo.createColorDefinition()
                color.setId("text_line_color" + "_" + spec_id)
                color.setColorValue(text_line_color_str)

                style = rInfo.createStyle("specStyle" + "_" + spec_id)
                style.getGroup().setFillColor("spec_fill_color" + "_" + spec_id)
                style.getGroup().setStroke("spec_border_color" + "_" + spec_id)
                style.getGroup().setStrokeWidth(spec_border_width)
                style.addType("SPECIESGLYPH")
                style.addId(specG_id)
                #style.addId(spec_id)
                if node.shape_index == 1 or node.shape_index == 6: #ellipse/text-outside
                    ellipse = style.getGroup().createEllipse()
                    ellipse.setCenter2D(RelAbsVector(0, 50), RelAbsVector(0, 50))
                    ellipse.setRadii(RelAbsVector(0, 50), RelAbsVector(0, 50))
                
                elif node.shape_index == 2: #hexagon(6)
                    polygon = style.getGroup().createPolygon()
                    renderPoint1 = polygon.createPoint()
                    renderPoint1.setCoordinates(RelAbsVector(0,100), RelAbsVector(0,50))
                    renderPoint2 = polygon.createPoint()
                    renderPoint2.setCoordinates(RelAbsVector(0,75), RelAbsVector(0,7))
                    renderPoint3 = polygon.createPoint()
                    renderPoint3.setCoordinates(RelAbsVector(0,25), RelAbsVector(0,7))
                    renderPoint4 = polygon.createPoint()
                    renderPoint4.setCoordinates(RelAbsVector(0,0), RelAbsVector(0,50))
                    renderPoint5 = polygon.createPoint()
                    renderPoint5.setCoordinates(RelAbsVector(0,25), RelAbsVector(0,86))
                    renderPoint6 = polygon.createPoint()
                    renderPoint6.setCoordinates(RelAbsVector(0,75), RelAbsVector(0,86))
                elif node.shape_index == 3: #line(2)
                    polygon = style.getGroup().createPolygon()
                    renderPoint1 = polygon.createPoint()
                    renderPoint1.setCoordinates(RelAbsVector(0,0), RelAbsVector(0,50))
                    renderPoint2 = polygon.createPoint()
                    renderPoint2.setCoordinates(RelAbsVector(0,100), RelAbsVector(0,50))
                elif node.shape_index == 4: #triangle(3)
                    polygon = style.getGroup().createPolygon()
                    renderPoint1 = polygon.createPoint()
                    renderPoint1.setCoordinates(RelAbsVector(0,100), RelAbsVector(0,50))
                    renderPoint2 = polygon.createPoint()
                    renderPoint2.setCoordinates(RelAbsVector(0,25), RelAbsVector(0,7))
                    renderPoint3 = polygon.createPoint()
                    renderPoint3.setCoordinates(RelAbsVector(0,25), RelAbsVector(0,86))
                else: #rectangle shape_index = 0/text-only 5/demo-combo 7/others as default (rectangle)
                    rectangle = style.getGroup().createRectangle()
                    rectangle.setCoordinatesAndSize(RelAbsVector(0,0),RelAbsVector(0,0),RelAbsVector(0,0),RelAbsVector(0,100),RelAbsVector(0,100))
                
                style = rInfo.createStyle("textStyle")
                style.getGroup().setStroke("text_line_color" + "_" + spec_id)
                style.getGroup().setStrokeWidth(1.)
                style.getGroup().setFontSize(RelAbsVector(text_font_size,0))
                style.getGroup().setTextAnchor('middle')
                style.getGroup().setVTextAnchor('middle')
                style.addType("TEXTGLYPH")
                style.addId(textG_id)


            if numReactions != 0:
                for i in range(len(allReactions)):
                    rxn_id = allReactions[i].id
                    reactionG_id = "ReactionG_" + rxn_id
                    reaction_fill_color     = allReactions[i].fill_color
                    reaction_fill_color_str = '#%02x%02x%02x%02x' % (reaction_fill_color.r,reaction_fill_color.g,reaction_fill_color.b,reaction_fill_color.a)           
                    reaction_line_thickness = allReactions[i].line_thickness

                    color = rInfo.createColorDefinition()
                    color.setId("reaction_fill_color" + "_" + rxn_id)
                    color.setColorValue(reaction_fill_color_str)

                    style = rInfo.createStyle("reactionStyle" + "_" + rxn_id)
                    style.getGroup().setStroke("reaction_fill_color" + "_" + rxn_id)
                    style.getGroup().setStrokeWidth(reaction_line_thickness)
                    style.addType("REACTIONGLYPH")
                    style.addId(reactionG_id)
                    #style.addId(reaction_id)

                    rct_num = len(allReactions[i].sources)
                    prd_num = len(allReactions[i].targets)
                    mod_num = len(allReactions[i].modifiers)

                    lineEnding = rInfo.createLineEnding()
                    lineEnding_id = '_line_ending_default_NONE_' + rxn_id
                    lineEnding.setId(lineEnding_id)
                    bb_id = "bb_" + lineEnding_id
                    [pos_x, pos_y] = [0., 0.]
                    [width, height] = [0., 0.]
                    lineEnding.setEnableRotationalMapping(True)
                    lineEnding.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x, pos_y, width, height))

                    fill_color_str = reaction_fill_color_str
                    color = rInfo.createColorDefinition()
                    color.setId("lineEnding_fill_color" + "_" + lineEnding_id)
                    color.setColorValue(fill_color_str)
                    lineEnding.getGroup().setFill('lineEnding_fill_color' + '_' + lineEnding_id)
            
                    border_color_str = reaction_fill_color_str
                    color = rInfo.createColorDefinition()
                    color.setId("lineEnding_border_color" + "_" + lineEnding_id)
                    color.setColorValue(border_color_str)
                    lineEnding.getGroup().setStroke('lineEnding_border_color' + '_' + lineEnding_id)


                    for j in range(rct_num):
                        specsRefG_id = "SpecRefG_" + rxn_id + "_rct" + str(j)
                        style = rInfo.createStyle("specRefGlyphStyle" + rxn_id + "_rct" + str(j))
                        style.getGroup().setEndHead('_line_ending_default_NONE_' + rxn_id)
                        style.getGroup().setStroke("lineEnding_border_color" + "_" + lineEnding_id)
                        style.getGroup().setFill("lineEnding_fill_color" + "_" + lineEnding_id)
                        style.getGroup().setStrokeWidth(reaction_line_thickness)
                        style.addType('SPECIESREFERENCEGLYPH')
                        style.addId(specsRefG_id)
                    
                    ##
                    lineEnding = rInfo.createLineEnding()
                    lineEnding_id = 'line_ending_' + rxn_id
                    lineEnding.setId(lineEnding_id)

                    bb_id = "bb_" + lineEnding_id
                    reaction_arrow_head_size = [reaction_line_thickness*5, reaction_line_thickness*4]
                    [pos_x, pos_y] = [-reaction_arrow_head_size[0], -0.5*reaction_arrow_head_size[1]]
                    [width, height] = reaction_arrow_head_size

                    lineEnding.setEnableRotationalMapping(True)
                    lineEnding.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x, pos_y, width, height))

                    fill_color_str = reaction_fill_color_str
                    color = rInfo.createColorDefinition()
                    color.setId("lineEnding_fill_color" + "_" + lineEnding_id)
                    color.setColorValue(fill_color_str)
                    lineEnding.getGroup().setFill('lineEnding_fill_color' + '_' + lineEnding_id)
            
                    border_color_str = reaction_fill_color_str
                    color = rInfo.createColorDefinition()
                    color.setId("lineEnding_border_color" + "_" + lineEnding_id)
                    color.setColorValue(border_color_str)
                    lineEnding.getGroup().setStroke('lineEnding_border_color' + '_' + lineEnding_id)

                    polygon = lineEnding.getGroup().createPolygon()
                    shape_info_list = [[0.,0.], [100.,50.], [0.,100.], [0.,0.]]
                    for k in range(len(shape_info_list)):
                        x = shape_info_list[k][0]
                        y = shape_info_list[k][1]                           
                        renderPoint = polygon.createPoint()
                        renderPoint.setCoordinates(RelAbsVector(0,x), RelAbsVector(0,y))

                    for j in range(prd_num):
                        specsRefG_id = "SpecRefG_" + rxn_id + "_prd" + str(j)
                        style = rInfo.createStyle("specRefGlyphStyle" + rxn_id + "_prd" + str(j))
                        style.getGroup().setEndHead(lineEnding_id)
                        style.getGroup().setStroke("lineEnding_border_color" + "_" + lineEnding_id)
                        style.getGroup().setFill("lineEnding_fill_color" + "_" + lineEnding_id)
                        style.getGroup().setStrokeWidth(reaction_line_thickness)
                        style.addType('SPECIESREFERENCEGLYPH')
                        style.addId(specsRefG_id)

                    ##
                    lineEnding = rInfo.createLineEnding()
                    lineEnding_mod_id = 'line_ending_modifier_' + rxn_id
                    lineEnding.setId(lineEnding_mod_id)

                    bb_id = "bb_" + lineEnding_mod_id
                    [pos_x, pos_y] = [-1.*reaction_line_thickness, 0.]
                    [width, height] = [2*reaction_line_thickness, 2*reaction_line_thickness]

                    lineEnding.setEnableRotationalMapping(True)
                    lineEnding.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x, pos_y, width, height))

                    fill_color_str = reaction_fill_color_str
                    color = rInfo.createColorDefinition()
                    color.setId("lineEnding_fill_color" + "_" + lineEnding_mod_id)
                    color.setColorValue(fill_color_str)
                    #lineEnding.getGroup().setFill('lineEnding_fill_color' + '_' + lineEnding_mod_id)
                    lineEnding.getGroup().setFill("_default_modifier_color_")

                    border_color_str = reaction_fill_color_str
                    color = rInfo.createColorDefinition()
                    color.setId("lineEnding_border_color" + "_" + lineEnding_mod_id)
                    color.setColorValue(border_color_str)
                    #lineEnding.getGroup().setStroke('lineEnding_border_color' + '_' + lineEnding_mod_id)
                    lineEnding.getGroup().setStroke("_default_modifier_color_")

                    ellipse = lineEnding.getGroup().createEllipse()
                    ellipse.setCenter2D(RelAbsVector(0, 0.), RelAbsVector(0, 0.))
                    ellipse.setRadii(RelAbsVector(0, 100.), RelAbsVector(0, 100.))

                    for j in range(mod_num):
                        specsRefG_id = "SpecRefG_" + rxn_id + "_mod" + str(j)
                        style = rInfo.createStyle("specRefGlyphStyle" + rxn_id + "_mod" + str(j))
                        style.getGroup().setEndHead(lineEnding_mod_id)
                        #style.getGroup().setStroke("reaction_fill_color" + "_" + rxn_id)
                        #style.getGroup().setFill("lineEnding_fill_color" + "_" + lineEnding_mod_id)
                        style.getGroup().setStroke("_default_modifier_color_")
                        style.getGroup().setFill("_default_modifier_color_")
                        style.getGroup().setStrokeWidth(reaction_line_thickness)
                        style.addType('SPECIESREFERENCEGLYPH')
                        style.addId(specsRefG_id)
            
            sbmlStr_layout_render = writeSBMLToString(doc)
            return sbmlStr_layout_render

    # def Save(self, evt):
    #     """
    #     Handler for the "Save" button.
    #     Save the SBML string to a file.
    #     """
    #     self.dirname=""  #set directory name to blank 
    #     dlg = wx.FileDialog(self.window, "Save As", self.dirname, wildcard="SBML files (*.xml)|*.xml", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
    #     if dlg.ShowModal() == wx.ID_OK:
    #         # Grab the content to be saved
    #         itcontains = self.SBMLText.GetValue()
    #         # Open the file for write, write, close
    #         self.filename=dlg.GetFilename()
    #         self.dirname=dlg.GetDirectory()
    #         filehandle=open(os.path.join(self.dirname, self.filename),'w')
    #         filehandle.write(itcontains)
    #         filehandle.close()
    #     # Get rid of the dialog to keep things tidy
    #     dlg.Destroy()



