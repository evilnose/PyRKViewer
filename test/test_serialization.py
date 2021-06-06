# pylint: disable=maybe-no-member
from test.api.common import DummyAppTest
from rkviewer import iodine
from rkviewer.plugin.api import Color
from rkviewer.config import Color
import unittest
import numpy as np

def createNode(nodeID, shapei= 0):
    #netID, nodeID, x, y, w, h, floatingNode, nodeLocked
    nodei = iodine.addNode(0, nodeID, 0.3, 0.4, 3, 4) 
    iodine.setNodeShapeIndex(0, nodei, shapei)
    return nodei

def createAlias(nodeID, shapei = 0):
    nodei = createNode(nodeID, shapei)
    iodine.addAliasNode(0, nodei, 0.3, 0.4, 3, 4)
    return nodei

def createReaction(reactants = list([["reactant", 0]]), products = list([["product", 0]]), 
                    sr_stoich = list([1]), dest_stoich = list([1])):
    """stoich lists of # species in reactants/products """
    source = []
    dest = []
    for i in range(len(reactants)):
        reactanti = createNode(*reactants[i])
        source.append(reactanti)

    for i in range(len(products)):
        producti = createNode(*products[i])
        dest.append(producti)
        

    iodine.createReaction(0, "test_rxn", source , dest)

    for stoich in range(len(sr_stoich)):
        iodine.setReactionSrcNodeStoich(0,0, source[stoich], sr_stoich[stoich])

    for stoich in range(len(dest_stoich)):
        iodine.setReactionDestNodeStoich(0,0, dest[stoich], dest_stoich[stoich])

def createCompartment(compids = [["comp0",[]]]):
    for comp in compids:
        compi = iodine.addCompartment(0, comp[0], 0, 0, 100, 100)
        for node in comp[1]:
            #add node
            nodei = createNode(*node)
            #move node to compartment
            iodine.setCompartmentOfNode(0, nodei, compi)

    #add following reaction

class TestSerialization(DummyAppTest):
    def setUp(self):
        iodine.newNetwork("net1")

    def testNode(self):
        node = createNode("node0")
        dump_object= iodine.dumpNetwork(0)
        self.assertEqual(0, len(dump_object["compartments"]))
        nodeDict = dump_object["nodes"]
        self.assertEqual(1, len(nodeDict))
        nodeObj = nodeDict[0]
        self.assertEqual(-1, nodeObj["compi"])
        self.assertIsInstance( nodeObj["floating"], bool)
        self.assertEqual(2, len(nodeObj["position"]))
        self.assertEqual(0.4, nodeObj["position"][1])
        self.assertEqual(2, len(nodeObj["rectSize"]))

    

    def testCompositeShape(self):
        #This test created specially for rectangle default shape
        node = createNode("node1")
        
        dump_object = iodine.dumpNetwork(0)
        nodeDict = dump_object["nodes"]
        shapeDict = nodeDict[0]["shape"]
    
        self.assertEqual("rectangle", shapeDict["name"])

        shape_items = shapeDict["items"][0]
        
        match_rectangle_primitive(self, shape_item = shape_items)
        
    def testTextPrimitive(self):
        node = createNode("node1")
        
        dump_object = iodine.dumpNetwork(0)
        nodeDict = dump_object["nodes"]
        shapeDict = nodeDict[0]["shape"]
        text_items = shapeDict["text_item"]
        
        self.assertIsInstance(text_items[0]["alignment"], str)
        self.assertEqual("center", text_items[0]["alignment"])
        self.assertEqual(4, len(text_items[0]["bg_color"]))
        self.assertEqual(3, len(text_items[0]["font_color"]))
        self.assertEqual("sans-serif", text_items[0]["font_family"])
        self.assertIsInstance(text_items[0]["font_size"], int)
        self.assertEqual("normal", text_items[0]["font_style"])
        self.assertEqual("normal", text_items[0]["font_weight"])

        self.assertIsInstance(text_items[1]["rotation"], float)
        self.assertEqual(2, len(text_items[1]["scale"]))
        self.assertEqual(2, len(text_items[1]["translation"]))

    def testMultipleNodes(self):
        #testing 100 nodes
        num_nodes = 100
        for i in range(num_nodes):
            createNode("node"+str(i), shapei = i%8)

        dump_object = iodine.dumpNetwork(0)
        nodeDict = dump_object["nodes"]
        self.assertEqual(num_nodes,len(nodeDict))

        for i in range(num_nodes):
            nodeObj = nodeDict[i]
            self.assertEqual(-1, nodeObj["compi"])
            self.assertIsInstance( nodeObj["floating"], bool)
            self.assertEqual(2, len(nodeObj["position"]))
            self.assertEqual(0.4, nodeObj["position"][1])
            self.assertEqual(2, len(nodeObj["rectSize"]))

    def testMultipleShapes(self):
        num_nodes = 100
        for i in range(num_nodes):
            createNode("node"+str(i), shapei = i%8)

        dump_object = iodine.dumpNetwork(0)
        nodeDict = dump_object["nodes"]

        shape_names = [shape.name for shape in iodine.shapeFactories]

        for i in range(num_nodes):
            shapeDict = nodeDict[i]["shape"]
            self.assertEqual(shape_names[i%8], shapeDict["name"])

            #check `text-only` shapes
            if shapeDict["name"] == "text-only":
                self.assertEqual(0, len(shapeDict["items"]))
                break

            shape_items = shapeDict["items"][0]
            

            if shapeDict["name"] =="rectangle":
                match_primitive(self, shape_items, "rectangle")
            elif shapeDict["name"] =="circle":
                match_primitive(self, shape_items, "circle")
            elif shapeDict["name"] == "text outside":
                #self.assertEqual("circle", shape_items[0]["name"])
                match_primitive(self, shape_items, "circle")
            elif shapeDict["name"] == "demo combo":
                match_primitive(self, shape_items[0], "circle")
                match_primitive(self, shape_items[1], "circle")
                match_primitive(self, shape_items, "rectangle")

    def testAlias(self):
        #since original node is at 0, alias is at 1
        anode = createAlias("node0")
        dump_object = iodine.dumpNetwork(0)

        nodeDict = dump_object["nodes"]
        self.assertEqual(2, len(nodeDict))
        anodeObj = nodeDict[1]
        self.assertIsInstance( anodeObj["nodeLocked"], bool)
        self.assertEqual(0, anodeObj["originalIdx"])
        self.assertEqual(2, len(anodeObj["position"]))
        self.assertEqual(2, len(anodeObj["rectSize"]))

    def testReaction(self):
        rxn = createReaction()
        dump_object = iodine.dumpNetwork(0)

        rxnDict = dump_object["reactions"]
        rxnObj = rxnDict[0]
        self.assertEqual(1, len(rxnDict))

        self.assertIsInstance(rxnObj["bezierCurves"], bool)
        self.assertEqual(2, len(rxnObj["centerHandlePos"]))
        self.assertEqual(None, rxnObj["centerPos"])
        self.assertEqual(3, len(rxnObj["fillColor"]))
        self.assertIsInstance(rxnObj["id"], str)
        self.assertIsInstance(rxnObj["modifiers"], list)
        self.assertIsInstance(rxnObj["rateLaw"], str)
        self.assertIsInstance(rxnObj["thickness"], float)
        self.assertEqual(rxnObj["tipStyle"], "circle")

    def testRxnCase1(self):
        """
        This test case against two seperate multiple reactant and product nodes
        """
        num_reactants = 11
        sr_stoich = np.random.randint(1, 6, size = num_reactants)
        reactant_ids = list(map(lambda i: 'sr'+str(i), np.arange(num_reactants)))
        reactants = list(zip(reactant_ids, sr_stoich))

        num_products = 13
        dest_stoich = np.random.randint(1, 6, size = num_products)
        product_ids = list(map(lambda i: 'dest'+str(i), np.arange(num_products)))
        products = list(zip(product_ids, dest_stoich))

        rxn = createReaction(reactants, products, sr_stoich = sr_stoich, dest_stoich = dest_stoich)
        
        dump_object = iodine.dumpNetwork(0)
        rxnDict = dump_object["reactions"]
        rxnObj = rxnDict[0]

        reactantObj = rxnObj["reactants"]
        productObj = rxnObj["products"]

        self.assertEqual(len(sr_stoich), len(reactantObj))
        self.assertEqual(len(dest_stoich), len(productObj))
        
        for i in reactantObj.keys():
            match_rxn_node(self, reactantObj[i], sr_stoich[i])
        
        for i in productObj.keys():
            match_rxn_node(self, productObj[i], dest_stoich[i-len(sr_stoich)])
    
    def testRxnCase2(self):
        """
        This test case is to examine a reaction with species existing in both reactant and product sides
        """
        sp_1 = ["e1", 0]
        sp_2 = ["e2", 0]

        node_1 = createNode(*sp_1)
        node_2 = createNode(*sp_2)
        
        iodine.createReaction(0, "test_rxn", [node_1] , [node_1, node_2])
        
        dump_object = iodine.dumpNetwork(0)
        rxnDict = dump_object["reactions"]
        rxnObj = rxnDict[0]

        reactantObj = rxnObj["reactants"]
        productObj = rxnObj["products"]

        self.assertEqual(1, len(reactantObj))
        self.assertEqual(2, len(productObj))

        for i in reactantObj.keys():
            match_rxn_node(self, reactantObj[i], 1.)
        
        for i in productObj.keys():
            match_rxn_node(self, productObj[i], 1.)

        #Checking if node 1 shows up in both reactant and product sides
        self.assertDictEqual(reactantObj[0], productObj[0])

    def testEmptyCompartment(self):
        comp = createCompartment()
        dump_object = iodine.dumpNetwork(0)
        compDict = dump_object["compartments"]
        self.assertEqual(1, len(compDict))
        compObj = compDict[0]
        
        self.assertEqual(3, len(compObj["fillColor"]))
        self.assertEqual("comp0", compObj["id"])
        self.assertEqual(3, len(compObj["outlineColor"]))
        self.assertIsInstance(compObj["outlineThickness"], float)
        self.assertEqual(2, len(compObj["position"]))
        self.assertEqual(2, len(compObj["rectSize"]))
        self.assertIsInstance(compObj["volume"], float)

    def testCompartmentWithNode(self):
        comp = createCompartment([["comp0", [["node0", 0], ["node1",2]]]])
        dump_object = iodine.dumpNetwork(0)
        compDict = dump_object["compartments"]
        self.assertEqual(1, len(compDict))
        compObj = compDict[0]
        #check if nodes are in comp
        nodeDict = dump_object["nodes"]
        self.assertEqual(2, len(nodeDict))
        self.assertEqual(0, nodeDict[0]['compi'])
        self.assertEqual(0, nodeDict[1]['compi'])
    
    def testCompartmentWithReaction(self):
        node_0 = ["node0", 0]
        node_1 = ["node1",2]
        comp = createCompartment([["comp0", [node_0, node_1]]])
        #rxn = createReaction(reactants = [node_0], products = [node_1])
        iodine.createReaction(0, "test_rxn", [0] , [1])
        dump_object = iodine.dumpNetwork(0)

        #check if nodes are in comp
        nodeDict = dump_object["nodes"]
        self.assertEqual(2, len(nodeDict))
        self.assertEqual(0, nodeDict[0]['compi'])
        self.assertEqual(0, nodeDict[1]['compi'])

        #check reaction:
        rxnDict = dump_object["reactions"]
        self.assertEqual(1, len(rxnDict))
        rxnObj = rxnDict[0]
        self.assertEqual(11, len(rxnObj))

    def testColorCompartment(self):
        comp = createCompartment()
        iodine.setCompartmentFillColor(0,0, color = Color(0, 0, 0, 100))
        iodine.setCompartmentOutlineColor(0, 0, color = Color(0, 0, 0, 100))
        dump_object = iodine.dumpNetwork(0)
        compDict = dump_object["compartments"]
        compObj = compDict[0]
        self.assertEqual(4, len(compObj["outlineColor"]))
        self.assertEqual(4, len(compObj["fillColor"]))

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
    test_obj.assertEqual("rectangle", shape_item[0]["name"])
    test_obj.assertIsInstance(shape_item[0]["corner_radius"], float)
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
    test_obj.assertEqual(poly_shapes[shape_name], len(shape_item[0]["points"]))
    [test_obj.assertEqual(2, len(point)) for point in shape_item[0]["points"]]
    
    #test transformation
    test_obj.assertIsInstance(shape_item[1]["rotation"], float)
    test_obj.assertEqual(2, len(shape_item[1]["scale"]))
    test_obj.assertEqual(2, len(shape_item[1]["translation"]))

def match_rxn_node(test_obj, node, stoich):
    test_obj.assertEqual(2, len(node["handlePos"]))
    test_obj.assertEqual(stoich, node["stoich"])
