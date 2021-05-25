# pylint: disable=maybe-no-member
from numpy.core.fromnumeric import shape
from numpy.lib.polynomial import poly
from test.api.common import TestWithApp
from typing import List
from rkviewer.canvas.data import Reaction
from rkviewer.mvc import CompartmentIndexError, NetIndexError, NodeIndexError, ReactionIndexError
from rkviewer import iodine
from rkplugin.api import Node, NodeData, Vec2
import unittest
import os
import json
import wx
import time


class TestDeserialization(TestWithApp):
    #def setUp(self):
        

    def tearDown(self):
        iodine.clearNetworks()

    def testNetwork(self):
        dirname = os.path.dirname(__file__)
        pathname = os.path.join(dirname, 'test.json')

        with open(pathname, 'r') as file:
            net_json = json.load(file)
        network = iodine.loadNetwork(net_json)
        iodine.validateState()

        dump_object = iodine.dumpNetwork(0)
        print(json.dumps(dump_object, indent = 4))
        self.assertDictEqual(net_json, dump_object)

        
        #self.assertEqual(0, iodine.getNetworkID(0))
        #node = iodine.getNodeID(0,0)
        #self.assertEqual()