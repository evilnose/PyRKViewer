# pylint: disable=maybe-no-member

from test.api.common import DummyAppTest
from rkviewer import iodine
import unittest
import os
import json



class TestDeserialization(DummyAppTest):
    #def setUp(self):
        

    def tearDown(self):
        iodine.clearNetworks()

    def testCompositeShape(self):
        '''Load network, validate its state, dump it, and compare the dumped object with the
        object before it was deserialized'''
        match_deserialized_object(self, "test_compositeShape.json")
    
    def testReaction(self):
        match_deserialized_object(self, "test_rxn.json")

    def testCompartment(self):
        match_deserialized_object(self, "test_comp.json")

    def testCompartmentWithRxn(self):
        match_deserialized_object(self, "test_comp_w_rxn.json")
    


def match_deserialized_object(test_obj, file):
    dirname = os.path.dirname(__file__)
    pathname = os.path.join(dirname, 'test.json')

    with open(pathname, 'r') as file:
        original_obj = json.load(file)

    iodine.loadNetwork(original_obj)
    iodine.validateState()

    test_obj.maxDiff = None
    dump_object = iodine.dumpNetwork(0)
    dumped_str = json.dumps(dump_object, indent=4, sort_keys=True)
    original_str = json.dumps(original_obj, indent=4, sort_keys=True)
    test_obj.assertEqual(original_str, dumped_str)

        
        