# pylint: disable=maybe-no-member
from test.api.common import DummyAppTest
from typing import List
from rkviewer.canvas.data import Reaction
from rkviewer.mvc import CompartmentIndexError, NetIndexError, NodeIndexError, ReactionIndexError
from rkplugin.api import Node, NodeData, Vec2
from rkplugin import api
import wx
import time


class TestNode(DummyAppTest):
    def test_add_basic(self):
        node = Node('Charles',
                    self.neti,
                    pos=Vec2(50, 50),
                    size=Vec2(50, 30))
        api.add_node(self.neti, id=node.id,
                        position=node.position,
                        size=node.size,
                        fill_color=api._to_color(wx.RED),  # HACK using API private methods
                        border_color=api._to_color(wx.BLUE),
                        border_width=2,
                        )
        nodes = api.get_nodes(self.neti)
        self.assertEqual(len(nodes), 1)
        self.assertEqual(0, nodes[0].index)
        expected = NodeData(id='Charles', net_index=self.neti, position=Vec2(50, 50), size=Vec2(50, 30), index=0)
        self.assertEqual(expected, nodes[0])
    
    #TODO test more properties

    def test_update_basic(self):
        api.add_node(self.neti, id="Eric")
        api.update_node(self.neti, 0, 'James')
        nodes = api.get_nodes(self.neti)
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].id, 'James')

    def test_update_failure(self):
        api.add_node(self.neti, id='Zulu')
        # empty ID
        with self.assertRaises(ValueError):
            api.update_node(self.neti, 0, id='')

        # nodes don't exist
        with self.assertRaises(NetIndexError):
            api.update_node(-1, 0, size=Vec2(50, 60))
        with self.assertRaises(NodeIndexError):
            api.update_node(0, 2, size=Vec2(50, 60))

        # out of bounds
        with self.assertRaises(ValueError):
            api.update_node(self.neti, 0, position=Vec2(-1, 0))
        with self.assertRaises(ValueError):
            api.update_node(self.neti, 0, position=Vec2(0, -1))

        csize = api.canvas_size()
        # in bounds
        api.update_node(self.neti, 0, position=csize - Vec2(100, 100))

        # out of bounds
        with self.assertRaises(ValueError):
            api.update_node(self.neti, 0, position=csize - Vec2(1, 1))


class TestAlias(DummyAppTest):
    def test_add_alias(self):
        nodei = api.add_node(self.neti, id='Hookie')
        api.add_alias(self.neti, nodei)

        nodes = api.get_nodes(self.neti)
        node_size = Vec2(50, 30)
        original = NodeData(net_index=self.neti, id='Hookie', index=0, original_index=-1, size=node_size)
        alias = NodeData(net_index=self.neti, id='Hookie', index=1, original_index=0, size=node_size)
        self.assertEqual(original, nodes[0])
        self.assertEqual(alias, nodes[1])

    def test_separate_props(self):
        '''Test modifying the properties of node and alias that are separate, i.e. not shared.
        
        As in, if the position of an alias is changed, that of the node should remain the same,
        and vice versa.
        '''
        alias_pos = Vec2(100, 100)
        alias_size = Vec2(50, 50)
        nodei = api.add_node(self.neti, id='Hookie')
        aliasi = api.add_alias(self.neti, nodei, position=alias_pos, size=alias_size)

        new_pos = Vec2(33, 33)
        new_size = Vec2(66, 66)
        new_lockNode = True
        api.update_node(self.neti, nodei, position=Vec2(33, 33), size=Vec2(66, 66), lockNode=True)
        node = api.get_node_by_index(self.neti, nodei)
        alias = api.get_node_by_index(self.neti, aliasi)

        # alias remains the same
        self.assertEqual(alias_pos, alias.position)
        self.assertEqual(alias_size, alias.size)
        self.assertEqual(False, alias.lockNode)

        # node is updated
        self.assertEqual(new_pos, node.position)
        self.assertEqual(new_size, node.size)
        self.assertEqual(new_lockNode, node.lockNode)

        # TODO also comp index

    def test_shared_props(self):
        pass  #TODO
