# pylint: disable=maybe-no-member
from typing import List
from rkviewer.canvas.data import Reaction
from rkviewer.mvc import CompartmentIndexError, NetIndexError, NodeIndexError, NodeNotFreeError
from rkplugin.api import Node, Vec2
from rkplugin import api
from test.utils import auto_compartment, auto_node, auto_reaction, close_app_context, open_app_context, run_app
import wx
import unittest
import time


# TODO add more tests
class TestNode(unittest.TestCase):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.neti = 0

    def test_add_nodes(self):
        with run_app():
            node = Node('Charles',
                        pos=Vec2(50, 50),
                        size=Vec2(50, 30),
                        fill_color=wx.RED,
                        border_color=wx.GREEN,
                        border_width=4)
            api.add_node(self.neti, node)
            nodes = api.get_nodes(self.neti)
            self.assertEqual(len(nodes), 1)
            self.assertEqual(0, nodes[0].index)
            self.assertTrue(node.props_equal(nodes[0]))

    def test_update_nodes(self):
        with run_app():
            node = Node('Charles',
                        pos=Vec2(50, 50),
                        size=Vec2(50, 30),
                        fill_color=wx.RED,
                        border_color=wx.GREEN,
                        border_width=4)
            api.add_node(self.neti, node)
            api.update_node(self.neti, 0, 'James')
            nodes = api.get_nodes(self.neti)
            self.assertEqual(len(nodes), 1)
            self.assertTrue(nodes[0].id_, 'James')

            with self.assertRaises(ValueError):
                api.update_node(self.neti, 0, id_='')
            with self.assertRaises(ValueError):
                api.update_node(self.neti, 0, position=Vec2(-1, 0))
            with self.assertRaises(ValueError):
                api.update_node(self.neti, 0, position=Vec2(-1, 0))

            csize = api.canvas_size()
            api.update_node(self.neti, 0, position=csize - Vec2(100, 100))
            with self.assertRaises(ValueError):
                api.update_node(self.neti, 0, position=csize - Vec2(1, 1))
            with self.assertRaises(NetIndexError):
                api.update_node(-1, 0, size=Vec2(50, 60))
            with self.assertRaises(NodeIndexError):
                api.update_node(0, 2, size=Vec2(50, 60))


class TestReaction(unittest.TestCase):
    def setUp(self):
        self.neti = 0
        self.app_handle = None
        self.app_handle = run_app()
        open_app_context(self.app_handle)
        api.add_node(self.neti, Node('Alice',
                                     pos=Vec2(50, 50),
                                     size=Vec2(50, 30),
                                     fill_color=wx.RED,
                                     border_color=wx.GREEN,
                                     border_width=4))
        api.add_node(self.neti, Node('Bob',
                                     pos=Vec2(150, 250),
                                     size=Vec2(50, 30),
                                     fill_color=wx.RED,
                                     border_color=wx.GREEN,
                                     border_width=4))
        api.add_node(self.neti, Node('Charlie',
                                     pos=Vec2(550, 450),
                                     size=Vec2(50, 30),
                                     fill_color=wx.RED,
                                     border_color=wx.GREEN,
                                     border_width=4))

    def tearDown(self):
        close_app_context(self.app_handle)

    def test_simple_reactions(self):
        rxn = auto_reaction('AB', [0], [1])
        api.add_reaction(self.neti, rxn)
        reactions = api.get_reactions(self.neti)
        self.assertEqual(1, len(reactions))
        self.assertEqual(1, len(reactions[0].sources))
        self.assertEqual(1, len(reactions[0].targets))
        self.assertEqual(0, reactions[0].sources[0])
        self.assertEqual(1, reactions[0].targets[0])

        with self.assertRaises(NodeNotFreeError):
            api.delete_node(self.neti, 0)
        with self.assertRaises(NodeNotFreeError):
            api.delete_node(self.neti, 1)

        api.delete_reaction(self.neti, 0)
        api.delete_node(self.neti, 0)
        api.delete_node(self.neti, 1)
        api.add_node(0, auto_node('Frederick II'))

        with self.assertRaises(ValueError):
            rxn = auto_reaction('circular', [2], [2])
            api.add_reaction(self.neti, rxn)

        with self.assertRaises(ValueError):
            rxn = auto_reaction('empty_reactants', [], [2])
            api.add_reaction(self.neti, rxn)

        with self.assertRaises(ValueError):
            rxn = auto_reaction('empty_products', [2], [])
            api.add_reaction(self.neti, rxn)


class TestCompartment(unittest.TestCase):
    def setUp(self):
        self.neti = 0
        self.app_handle = None
        self.app_handle = run_app()
        open_app_context(self.app_handle)
        api.add_node(self.neti, Node('Alice',
                                     pos=Vec2(50, 50),
                                     size=Vec2(50, 30),
                                     fill_color=wx.RED,
                                     border_color=wx.GREEN,
                                     border_width=4))
        api.add_node(self.neti, Node('Bob',
                                     pos=Vec2(150, 250),
                                     size=Vec2(50, 30),
                                     fill_color=wx.RED,
                                     border_color=wx.GREEN,
                                     border_width=4))
        api.add_node(self.neti, Node('Charlie',
                                     pos=Vec2(550, 450),
                                     size=Vec2(50, 30),
                                     fill_color=wx.RED,
                                     border_color=wx.GREEN,
                                     border_width=4))

    def tearDown(self):
        close_app_context(self.app_handle)

    def test_simple_compartments(self):
        self.assertEqual(api.get_nodes_in_compartment(self.neti, -1), [0, 1, 2])
        api.add_compartment(self.neti, auto_compartment('c_1'))
        api.set_compartment_of_node(self.neti, 0, 0)
        api.set_compartment_of_node(self.neti, 1, 0)
        self.assertEqual(api.get_nodes_in_compartment(self.neti, 0), [0, 1])
        api.set_compartment_of_node(self.neti, 0, -1)
        self.assertEqual(api.get_nodes_in_compartment(self.neti, 0), [1])
        self.assertEqual(api.get_nodes_in_compartment(self.neti, -1), [0, 2])
        self.assertEqual(api.get_compartment_of_node(self.neti, 1), 0)
        self.assertEqual(api.get_compartment_of_node(self.neti, 0), -1)
        self.assertEqual(api.get_compartment_of_node(self.neti, 2), -1)

        api.delete_compartment(self.neti, 0)
        self.assertEqual(set(api.get_nodes_in_compartment(self.neti, -1)), set([0, 1, 2]))
        with self.assertRaises(CompartmentIndexError):
            api.get_nodes_in_compartment(self.neti, 0)
