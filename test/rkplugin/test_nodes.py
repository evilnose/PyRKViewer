# pylint: disable=maybe-no-member
from rkplugin.api import Node, Vec2
from rkplugin import api
from test.utils import run_app
import wx
import unittest
import time


# TODO add more tests
class TestRectUtils(unittest.TestCase):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.neti = 0

    def test_add_nodes(self):
        with run_app():
            node = Node('Charles',
                        pos=Vec2(50, 50),
                        size=Vec2(40, 12),
                        fill_color=wx.RED,
                        border_color=wx.GREEN,
                        border_width=4)
            api.add_node(self.neti, node)
            nodes = api.all_nodes() 
            self.assertEqual(len(nodes), 1)
            self.assertEqual(0, nodes[0].index)
            self.assertTrue(node.props_equal(nodes[0]))

    def test_update_nodes(self):
        with run_app():
            node = Node('Charles',
                        pos=Vec2(50, 50),
                        size=Vec2(40, 12),
                        fill_color=wx.RED,
                        border_color=wx.GREEN,
                        border_width=4)
            api.add_node(self.neti, node)
            api.update_node(self.neti, 0, 'James')
            nodes = api.all_nodes() 
            self.assertEqual(len(nodes), 1)
            self.assertTrue(nodes[0].id_, 'James')
