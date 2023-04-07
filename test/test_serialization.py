# pylint: disable=maybe-no-member
from numpy.core.fromnumeric import shape
from numpy.lib.polynomial import poly
from test.api.common import DummyAppTest
from typing import List
from rkviewer.canvas.data import Reaction
from rkviewer.mvc import CompartmentIndexError, NetIndexError, NodeIndexError, ReactionIndexError
from rkviewer import iodine
from rkviewer.plugin.api import Node, NodeData, Vec2
import unittest
import wx
import time

def createNode(nodeID, shapei= 0):
    #netID, nodeID, x, y, w, h, floatingNode, nodeLocked
    nodei = iodine.addNode(0, nodeID, 0.3, 0.4, 3, 4) 
    iodine.setNodeShapeIndex(0, nodei, shapei)
    return nodei

def createAlias(nodeID, shapei = 0):
    nodei = createNode(nodeID, shapei)
    iodine.addAliasNode(0, nodei, 0.3, 0.4, 3, 4)
    return nodei

def createReaction():
    reactanti = createNode("reactant", 0)
    producti = createNode("product", 0)
    # reactant = iodine.TNode(0, "reactant", Vec2(0.3,0.4), Vec2(3,4), floating= True, 
    # nodeLocked= False)
    # product = iodine.TNode(1, "product", Vec2(0.6,0.8), Vec2(6,8), floating= True, 
    # nodeLocked= False)
    # rxn = iodine.TReaction("rxn1", reactants={0: iodine.TSpeciesNode(1, reactant.position)}, products= {1: iodine.TSpeciesNode(1, product.position)})
    # network = iodine.TNetwork("net1", {0:reactant,1:product}, reactions={0:rxn})
    # network.addReaction(rxn)
    iodine.createReaction(0, "rxn1", [reactanti], [producti])

def createCompartment():
    iodine.addCompartment(0, "comp0", 0, 0, 100, 100)
    iodine.addCompartment(0, "comp1", 0, 0, 100, 100)
    node = createNode("node0")
    #move node to compartment
    iodine.setCompartmentOfNode(0, 0, 0)

    #add following reaction

class TestSerialization(DummyAppTest):
    def setUp(self):
        iodine.newNetwork("net1")

    # def testNode(self):
    #     node = createNode("node0")
    #     dump_object= iodine.dumpNetwork(0)
    #     self.assertEqual(0, len(dump_object["compartments"]))
    #     nodeDict = dump_object["nodes"]
    #     self.assertEqual(1, len(nodeDict))
    #     nodeObj = nodeDict[0]
    #     self.assertEqual(-1, nodeObj["compi"])
    #     self.assertIsInstance( nodeObj["floating"], bool)
    #     self.assertEqual(2, len(nodeObj["position"]))
    #     self.assertEqual(0.4, nodeObj["position"][1])
    #     self.assertEqual(2, len(nodeObj["rectSize"]))

    

    # def testCompositeShape(self):
    #     #This test created specially for rectangle default shape
    #     node = createNode("node1")
        
    #     dump_object = iodine.dumpNetwork(0)
    #     nodeDict = dump_object["nodes"]
    #     shapeDict = nodeDict[0]["shape"]
    
    #     self.assertEqual("rectangle", shapeDict["name"])

    #     shape_items = shapeDict["items"][0]
        
    #     match_rectangle_primitive(self, shape_item = shape_items)
        # self.assertEqual(3, len(shape_items[0]["border_color"]))
        # self.assertIsInstance(shape_items[0]["border_width"], float)
        # self.assertEqual("rectangle", shape_items[0]["name"])
        # self.assertIsInstance(shape_items[0]["corner_radius"], float)
        # self.assertEqual(4, len(shape_items[0]["fill_color"]))

        # self.assertIsInstance(shape_items[1]["rotation"], float)
        # self.assertEqual(2, len(shape_items[1]["scale"]))
        # self.assertEqual(2, len(shape_items[1]["translation"]))
        
    # def testTextPrimitive(self):
    #     node = createNode("node1")
        
    #     dump_object = iodine.dumpNetwork(0)
    #     nodeDict = dump_object["nodes"]
    #     shapeDict = nodeDict[0]["shape"]
    #     text_items = shapeDict["text_item"]
        
    #     self.assertIsInstance(text_items[0]["alignment"], str)
    #     self.assertEqual("center", text_items[0]["alignment"])
    #     self.assertEqual(4, len(text_items[0]["bg_color"]))
    #     self.assertEqual(3, len(text_items[0]["font_color"]))
    #     self.assertEqual("sans-serif", text_items[0]["font_family"])
    #     self.assertIsInstance(text_items[0]["font_size"], int)
    #     self.assertEqual("normal", text_items[0]["font_style"])
    #     self.assertEqual("normal", text_items[0]["font_weight"])

    #     self.assertIsInstance(text_items[1]["rotation"], float)
    #     self.assertEqual(2, len(text_items[1]["scale"]))
    #     self.assertEqual(2, len(text_items[1]["translation"]))

    # def testMultipleNodes(self):
    #     #testing 100 nodes
    #     num_nodes = 100
    #     for i in range(num_nodes):
    #         createNode("node"+str(i), shapei = i%6) #see the length of shapeFactories in iodine.py

    #     dump_object = iodine.dumpNetwork(0)
    #     nodeDict = dump_object["nodes"]
    #     self.assertEqual(num_nodes,len(nodeDict))

    #     for i in range(num_nodes):
    #         nodeObj = nodeDict[i]
    #         self.assertEqual(-1, nodeObj["compi"])
    #         self.assertIsInstance( nodeObj["floating"], bool)
    #         self.assertEqual(2, len(nodeObj["position"]))
    #         self.assertEqual(0.4, nodeObj["position"][1])
    #         self.assertEqual(2, len(nodeObj["rectSize"]))

    # def testMultipleShapes(self):
    #     num_nodes = 100
    #     for i in range(num_nodes):
    #         createNode("node"+str(i), shapei = i%6)

    #     dump_object = iodine.dumpNetwork(0)
    #     nodeDict = dump_object["nodes"]

    #     shape_names = [shape.name for shape in iodine.shapeFactories]

    #     for i in range(num_nodes):
    #         shapeDict = nodeDict[i]["shape"]
    #         #self.assertEqual(shape_names[i%6], shapeDict["name"]) #shapeDict["name"] is always 'rectangle'

    #         #check `text-only` shapes
    #         if shapeDict["name"] == "text-only":
    #             self.assertEqual(0, len(shapeDict["items"]))
    #             break

    #         shape_items = shapeDict["items"][0]
            

    #         if shapeDict["name"] =="rectangle":
    #             match_primitive(self, shape_items, "rectangle")
    #         elif shapeDict["name"] =="circle":
    #             match_primitive(self, shape_items, "circle")
    #         elif shapeDict["name"] == "text outside":
    #             #self.assertEqual("circle", shape_items[0]["name"])
    #             match_primitive(self, shape_items, "circle")
    #         elif shapeDict["name"] == "demo combo":
    #            match_primitive(self, shape_items[0], "circle")
    #            match_primitive(self, shape_items[1], "circle")
    #            match_primitive(self, shape_items, "rectangle")

    # def testAlias(self):
    #     #since original node is at 0, alias is at 1
    #     anode = createAlias("node0")
    #     dump_object = iodine.dumpNetwork(0)

    #     nodeDict = dump_object["nodes"]
    #     self.assertEqual(2, len(nodeDict))
    #     anodeObj = nodeDict[1]
    #     self.assertIsInstance( anodeObj["nodeLocked"], bool)
    #     self.assertEqual(0, anodeObj["originalIdx"])
    #     self.assertEqual(2, len(anodeObj["position"]))
    #     self.assertEqual(2, len(anodeObj["rectSize"]))
    
    def testCompartment(self):
        #compartment with no node
        #a node in compartment
        # compartment with reaction
        pass

    # def testReaction(self):
    #     rxn = createReaction()
    #     dump_object = iodine.dumpNetwork(0)

    #     rxnDict = dump_object["reactions"]
    #     print(rxnDict)
    #     self.assertEqual(1, len(rxnDict))

        #a node as a reactant and product: 0 as reactant, 0 and 1 are products
        #multiple reactants and products

    def tearDown(self):
        iodine.clearNetworks()



poly_shapes = {
    'circle':0,
    'rectangle':4,
    'hexagon':6,
    'triangle':3,
    'line':2
}
def match_primitive(test_obj, shape_item, shape_name):
    if shape_name == "rectangle":
        match_rectangle_primitive(test_obj, shape_item)
    elif shape_name =="circle":
        match_circle_primitive(test_obj, shape_item)
    else:
        match_polygon_primitive(test_obj, shape_item, shape_name)

def match_rectangle_primitive(test_obj, shape_item):
    test_obj.assertEqual(3, len(shape_item[0]["border_color"]))
    test_obj.assertIsInstance(shape_item[0]["border_width"], float)
    #test_obj.assertEqual("rectangle", shape_item[0]["name"]) #different shape names
    #test_obj.assertIsInstance(shape_item[0]["corner_radius"], float) # does not always exit
    test_obj.assertEqual(4, len(shape_item[0]["fill_color"]))

    #test transformation
    test_obj.assertIsInstance(shape_item[1]["rotation"], float)
    test_obj.assertEqual(2, len(shape_item[1]["scale"]))
    test_obj.assertEqual(2, len(shape_item[1]["translation"]))

def match_circle_primitive(test_obj, shape_item):
    test_obj.assertEqual(3, len(shape_item[0]["border_color"]))
    test_obj.assertIsInstance(shape_item[0]["border_width"], float)
    test_obj.assertEqual("circle", shape_item[0]["name"])
    test_obj.assertEqual(4, len(shape_item[0]["fill_color"]))

    #test transformation
    test_obj.assertIsInstance(shape_item[1]["rotation"], float)
    test_obj.assertEqual(2, len(shape_item[1]["scale"]))
    test_obj.assertEqual(2, len(shape_item[1]["translation"]))

def match_polygon_primitive(test_obj, shape_item, shape_name):
    test_obj.assertEqual(3, len(shape_item[0]["border_color"]))
    test_obj.assertIsInstance(shape_item[0]["border_width"], float)
    test_obj.assertEqual(4, len(shape_item[0]["fill_color"]))
    test_obj.assertIsInstance(shape_item[0]["radius"], float)
    test_obj.assertEqual(polygon_shapes[shape_name], len(shape_item[0]["points"]))
    [test_obj.assertEqual(2, len(point)) for point in shape_item[0]["points"]]
    
    #test transformation
    test_obj.assertIsInstance(shape_item[1]["rotation"], float)
    test_obj.assertEqual(2, len(shape_item[1]["scale"]))
    test_obj.assertEqual(2, len(shape_item[1]["translation"]))
