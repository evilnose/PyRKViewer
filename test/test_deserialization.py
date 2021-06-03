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
import os
import json
import wx
import time


class TestDeserialization(DummyAppTest):
    #def setUp(self):
        

    def tearDown(self):
        iodine.clearNetworks()

    def testNetwork(self):
        '''Load network, validate its state, dump it, and compare the dumped object with the
        object before it was deserialized'''
        dirname = os.path.dirname(__file__)
        pathname = os.path.join(dirname, 'test.json')

        with open(pathname, 'r') as file:
            original_obj = json.load(file)

        iodine.loadNetwork(original_obj)
        iodine.validateState()

        self.maxDiff = None
        dump_object = iodine.dumpNetwork(0)
        dumped_str = json.dumps(dump_object, indent=4, sort_keys=True)
        original_str = json.dumps(original_obj, indent=4, sort_keys=True)
        self.assertEqual(original_str, dumped_str)

        
        #self.assertEqual(0, iodine.getNetworkID(0))
        #node = iodine.getNodeID(0,0)
        #self.assertEqual()