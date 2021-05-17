"""
Export the network on canvas to an SBML string as save it as a file.
Version 0.02: Author: Jin Xu (2021)
"""


# pylint: disable=maybe-no-member

from inspect import Parameter
#from libsbml import KineticLaw
#from tesbml.libsbml import BoundaryCondition
import wx
from rkplugin.plugins import PluginMetadata, WindowedPlugin, PluginCategory
from rkplugin import api
from rkplugin.api import Node, Vec2, Reaction, Color
import os
from libsbml import * # does not have to import in the main.py too

class ExportSBML(WindowedPlugin):
    metadata = PluginMetadata(
        name='ExportSBML',
        author='Jin Xu',
        version='0.0.2',
        short_desc='Export SBML.',
        long_desc='Export the SBML String from the network on canvas and save it to a file.',
        category=PluginCategory.ANALYSIS
    )


    def create_window(self, dialog):
        """
        Create a window to export the SBML.
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
        numReactions = api.reaction_count(netIn)
        
        if numNodes == 0: #or numReactions == 0 :
            wx.MessageBox("Please import a network on canvas", "Message", wx.OK | wx.ICON_INFORMATION)
        else:
            allNodes = api.get_nodes(netIn)
            allReactions = api.get_reactions(netIn)
            allcompartments = api.get_compartments(netIn)
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
            model.setId("Model_layout")
            document.setModel(model)

            # create the Compartment and species
            if numCompartments != 0:
                for i in range(numCompartments):   
                    compartment = model.createCompartment()
                    comp_id=allcompartments[i].id
                    compartment.setId(comp_id)
                    compartment.setConstant(True)
                    for j in range(len(allcompartments[i].nodes)):
                        spec_id = allNodes[allcompartments[i].nodes[j]].id
                        species = model.createSpecies()
                        species.setId(spec_id)
                        species.setCompartment(comp_id)
                        species.setInitialConcentration(1.0)	
                        species.setHasOnlySubstanceUnits(False)
                        species.setBoundaryCondition(False)
                        species.setConstant(False)             
                        if allNodes[allcompartments[i].nodes[j]].floatingNode == False:
                            species.setBoundaryCondition(True)
            else: #set default compartment
                compartment = model.createCompartment()
                comp_id="c_0"
                compartment.setId(comp_id)
                compartment.setConstant(True)
                for i in range(numNodes):
                    spec_id = allNodes[i].id
                    species = model.createSpecies()
                    species.setId(spec_id)
                    species.setCompartment(comp_id)
                    species.setInitialConcentration(1.0)	
                    species.setHasOnlySubstanceUnits(False)
                    species.setBoundaryCondition(False)
                    species.setConstant(False)             
                    if allNodes[i].floatingNode == False:
                        species.setBoundaryCondition(True)
                        species.setConstant(True)

            # create reactions:
            for i in range(numReactions):
                reaction_id = allReactions[i].id
                rct = [] # id list of the rcts
                prd = []
                rct_num = len(allReactions[i].sources)
                prd_num = len(allReactions[i].targets)
                for j in range(rct_num):
                    rct.append(allNodes[allReactions[i].sources[j]].id)
                for j in range(prd_num):
                    prd.append(allNodes[allReactions[i].targets[j]].id)

                kinetic_law = ''
                parameter_list = []
                kinetic_law = kinetic_law + 'E' + str (i) + '*(k' + str (i) 
                parameter_list.append('E' + str (i))
                parameter_list.append('k' + str (i))
                for j in range(rct_num):
                    kinetic_law = kinetic_law + '*' + rct[j]
                    
                reaction = model.createReaction()
                reaction.setId(allReactions[i].id)
                reaction.setReversible(False)
                reaction.setFast(False)
                if isReversible:
                    reaction.setReversible(True)
                    kinetic_law = kinetic_law + ' - k' + str (i) + 'r'
                    parameter_list.append('k' + str (i) + 'r')
                    for j in range(prd_num):
                        kinetic_law = kinetic_law + '*' + prd[j]
                kinetic_law = kinetic_law + ')'
                for j in range(len(parameter_list)):
                    parameters = model.createParameter()
                    parameters.setId(parameter_list[j])
                    parameters.setValue(0.1)
                    parameters.setConstant(True)
                kinetics = reaction.createKineticLaw()
                kinetics.setFormula(kinetic_law)
                

                for j in range(rct_num):
                    reference = reaction.createReactant()
                    reference.setSpecies(rct[j])
                    ref_id = "SpecRef_" + reaction_id + "_rct" + str(j)
                    reference.setId(ref_id)
                    reference.setStoichiometry(1.)
                    reference.setConstant(False)

                for j in range(prd_num):
                    reference = reaction.createProduct()
                    reference.setSpecies(prd[j])
                    ref_id = "SpecRef_" + reaction_id + "_prd" + str(j)
                    reference.setId(ref_id)
                    reference.setStoichiometry(1.)
                    reference.setConstant(False)

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
            layout.setId("Layout_1")
            layout.setDimensions(Dimensions(layoutns, 800.0, 800.0))
            # random network (40+800x, 40+800y)

            #create the CompartmentGlyph and SpeciesGlyphs

            if numCompartments != 0:
                for i in range(numCompartments):   
                    comp_id=allcompartments[i].id

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
                    for j in range(len(allcompartments[i].nodes)):
                        spec_id = allNodes[allcompartments[i].nodes[j]].id
                        speciesGlyph = layout.createSpeciesGlyph()
                        specG_id = "SpecG_" + spec_id
                        speciesGlyph.setId(specG_id)
                        speciesGlyph.setSpeciesId(spec_id)
                        bb_id  = "bb_" + spec_id
                        pos_x  = allNodes[allcompartments[i].nodes[j]].position.x
                        pos_y  = allNodes[allcompartments[i].nodes[j]].position.y
                        width  = allNodes[allcompartments[i].nodes[j]].size.x
                        height = allNodes[allcompartments[i].nodes[j]].size.y
                        speciesGlyph.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x, pos_y, width, height))

                        textGlyph = layout.createTextGlyph()
                        textG_id = "TextG_" + spec_id
                        textGlyph.setId(textG_id)
                        bb_id = "bb_spec_text_" + spec_id
                        textGlyph.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x, pos_y, width, height))
                        textGlyph.setOriginOfTextId(specG_id)
                        textGlyph.setGraphicalObjectId(specG_id)
            else:#there is no compartment   
                for i in range(numNodes):
                    spec_id = allNodes[i].id
                    speciesGlyph = layout.createSpeciesGlyph()
                    specG_id = "SpecG_" + spec_id
                    speciesGlyph.setId(specG_id)
                    speciesGlyph.setSpeciesId(spec_id)
                    bb_id  = "bb_" + spec_id
                    pos_x  = allNodes[i].position.x
                    pos_y  = allNodes[i].position.y
                    width  = allNodes[i].size.x
                    height = allNodes[i].size.y
                    speciesGlyph.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x, pos_y, width, height))

                    textGlyph = layout.createTextGlyph()
                    textG_id = "TextG_" + spec_id
                    textGlyph.setId(textG_id)
                    bb_id = "bb_spec_text_" + spec_id
                    textGlyph.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x, pos_y, width, height))
                    textGlyph.setOriginOfTextId(specG_id)
                    textGlyph.setGraphicalObjectId(specG_id)

            # create the ReactionGlyphs and SpeciesReferenceGlyphs
            for i in range(numReactions):
                reaction_id = allReactions[i].id
                reactionGlyph = layout.createReactionGlyph()
                reactionG_id = "RectionG_" + reaction_id
                reactionGlyph.setId(reactionG_id)
                reactionGlyph.setReactionId(reaction_id)
                
                reactionCurve = reactionGlyph.getCurve()
                ls = reactionCurve.createLineSegment()
                centroid = api.compute_centroid(0, allReactions[i].sources, allReactions[i].targets)
                ls.setStart(Point(layoutns, centroid.x, centroid.y))
                ls.setEnd(Point(layoutns, centroid.x, centroid.y))

                rct = [] # id list of the rcts
                prd = []
                rct_num = len(allReactions[i].sources)
                prd_num = len(allReactions[i].targets)
                for j in range(rct_num):
                    rct.append(allNodes[allReactions[i].sources[j]].id)
                for j in range(prd_num):
                    prd.append(allNodes[allReactions[i].targets[j]].id)

                for j in range(rct_num):
                    ref_id = "SpecRef_" + reaction_id + "_rct" + str(j)

                    speciesReferenceGlyph = reactionGlyph.createSpeciesReferenceGlyph()
                    specsRefG_id = "SpecRefG_" + reaction_id + "_rct" + str(j)
                    specG_id = "SpecG_" + rct[j]
                    speciesReferenceGlyph.setId(specsRefG_id)
                    speciesReferenceGlyph.setSpeciesGlyphId(specG_id)
                    speciesReferenceGlyph.setSpeciesReferenceId(ref_id)
                    speciesReferenceGlyph.setRole(SPECIES_ROLE_UNDEFINED)

                    speciesReferenceCurve = speciesReferenceGlyph.getCurve()
                    cb = speciesReferenceCurve.createCubicBezier()
                    #cb = speciesReferenceCurve.createLineSegment()

                    cb.setStart(Point(layoutns, centroid.x, centroid.y))

                    handles = api.default_handle_positions(netIn, allReactions[i].index)
                    pos_x = handles[1+j].x
                    pos_y = handles[1+j].y
                    cb.setBasePoint1(Point(layoutns, pos_x, pos_y))
                    cb.setBasePoint2(Point(layoutns, pos_x, pos_y))

                    pos_x = allNodes[allReactions[i].sources[j]].position.x
                    pos_y = allNodes[allReactions[i].sources[j]].position.y
                    width = allNodes[allReactions[i].sources[j]].size.x
                    height = allNodes[allReactions[i].sources[j]].size.y
                    cb.setEnd(Point(layoutns, pos_x + 0.5*width, pos_y - 0.5*height))

                for j in range(prd_num):
                    ref_id = "SpecRef_" + reaction_id + "_prd" + str(j)
                    speciesReferenceGlyph = reactionGlyph.createSpeciesReferenceGlyph()
                    specsRefG_id = "SpecRefG_" + reaction_id + "_prd" + str(j)
                    specG_id = "SpecG_" + prd[j]
                    speciesReferenceGlyph.setId(specsRefG_id)
                    speciesReferenceGlyph.setSpeciesGlyphId(specG_id)
                    speciesReferenceGlyph.setSpeciesReferenceId(ref_id)
                    speciesReferenceGlyph.setRole(SPECIES_ROLE_UNDEFINED)

                    speciesReferenceCurve = speciesReferenceGlyph.getCurve()
                    cb = speciesReferenceCurve.createCubicBezier()
                    #cb = speciesReferenceCurve.createLineSegment()
                    cb.setStart(Point(layoutns, centroid.x, centroid.y))

                    handles = api.default_handle_positions(netIn, allReactions[i].index)
                    pos_x = handles[1+j].x
                    pos_y = handles[1+j].y
                    cb.setBasePoint1(Point(layoutns, pos_x, pos_y))
                    cb.setBasePoint2(Point(layoutns, pos_x, pos_y))

                    pos_x = allNodes[allReactions[i].targets[j]].position.x
                    pos_y = allNodes[allReactions[i].targets[j]].position.y
                    width = allNodes[allReactions[i].targets[j]].size.x
                    height = allNodes[allReactions[i].targets[j]].size.y
                    cb.setEnd(Point(layoutns, pos_x + 0.5*width, pos_y - 0.5*height))

            sbmlStr_layout = writeSBMLToString(document) #sbmlStr is w/o layout info
            #self.SBMLText.SetValue(sbmlStr_layout) 

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

            # add some colors
            if numCompartments != 0:  
                fill_color        = allcompartments[0].fill_color
                border_color      = allcompartments[0].border_color
                comp_border_width = allcompartments[0].border_width
                fill_color_str    = '#%02x%02x%02x' % (fill_color.r,fill_color.g,fill_color.b)
                border_color_str  = '#%02x%02x%02x' % (border_color.r,border_color.g,border_color.b)
            
            else:
                comp_border_width = 2.
                fill_color_str    = '#9ea9ff'
                border_color_str  = '#001dff'

            #nodeData does not have fill_color,border_color,border_width
            node =  allNodes[0]
            # spec_fill_color   = node.fill_color
            # spec_border_color = node.border_color
            # spec_border_width = node.border_width
            # spec_fill_color_str   = '#%02x%02x%02x' % (spec_fill_color.r,spec_fill_color.g,spec_fill_color.b)
            # spec_border_color_str = '#%02x%02x%02x' % (spec_border_color.r,spec_border_color.g,spec_border_color.b)

            spec_fill_color_str = '#ffcc99'
            spec_border_color_str = '#ff6c09'
            spec_border_width = 2.

            if numReactions != 0:
                reaction_fill_color     = allReactions[0].fill_color
                reaction_fill_color_str = '#%02x%02x%02x' % (reaction_fill_color.r,reaction_fill_color.g,reaction_fill_color.b)           
                reaction_line_thickness = allReactions[i].line_thickness

            #add some colors
            color = rInfo.createColorDefinition()
            color.setId("black")
            color.setColorValue("#000000")

            color = rInfo.createColorDefinition()
            color.setId("comp_fill_color")
            color.setColorValue(fill_color_str)

            color = rInfo.createColorDefinition()
            color.setId("comp_border_color")
            color.setColorValue(border_color_str)

            color = rInfo.createColorDefinition()
            color.setId("spec_fill_color")
            color.setColorValue(spec_fill_color_str)

            color = rInfo.createColorDefinition()
            color.setId("spec_border_color")
            color.setColorValue(spec_border_color_str)

            if numReactions != 0:
                color = rInfo.createColorDefinition()
                color.setId("reaction_fill_color")
                color.setColorValue(reaction_fill_color_str)

            # add a list of styles 
            style = rInfo.createStyle("compStyle")
            style.getGroup().setFillColor("comp_fill_color")
            style.getGroup().setStroke("comp_border_color")
            style.getGroup().setStrokeWidth(comp_border_width)
            style.addType("COMPARTMENTGLYPH")
            rectangle = style.getGroup().createRectangle()
            rectangle.setCoordinatesAndSize(RelAbsVector(0,0),RelAbsVector(0,0),RelAbsVector(0,0),RelAbsVector(0,100),RelAbsVector(0,100))

            style = rInfo.createStyle("specStyle")
            style.getGroup().setFillColor("spec_fill_color")
            style.getGroup().setStroke("spec_border_color")
            style.getGroup().setStrokeWidth(spec_border_width)
            style.addType("SPECIESGLYPH")
            rectangle = style.getGroup().createRectangle()
            rectangle.setCoordinatesAndSize(RelAbsVector(0,0),RelAbsVector(0,0),RelAbsVector(0,0),RelAbsVector(0,100),RelAbsVector(0,100))

            style = rInfo.createStyle("textStyle")
            style.getGroup().setStroke("black")
            style.getGroup().setStrokeWidth(1.)
            style.addType("TEXTGLYPH")

            if numReactions != 0:
                style = rInfo.createStyle("reactionStyle")
                style.getGroup().setStroke("reaction_fill_color")
                style.getGroup().setStrokeWidth(reaction_line_thickness)
                style.addType("REACTIONGLYPH SPECIESREFERENCEGLYPH")
            
            
            sbmlStr_layout_render = writeSBMLToString(doc)
            self.SBMLText.SetValue(sbmlStr_layout_render) 
           
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



