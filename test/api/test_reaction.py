
from test.api.common import DummyAppTest

from rkplugin.api import Node, Vec2
from rkplugin import api
from rkviewer.mvc import NodeNotFreeError, NodeIndexError, ReactionIndexError


class TestReaction(DummyAppTest):
    def setUp(self):
        api.add_node(self.neti, 'Alice')
        api.add_node(self.neti, 'Bob')
        api.add_node(self.neti, 'Charlie')

    def test_add_basic(self):
        """Simple tests for reactions."""
        api.add_reaction(self.neti, 'AB', [0], [1])
        reactions = api.get_reactions(self.neti)
        self.assertEqual(1, len(reactions))
        self.assertEqual(1, len(reactions[0].sources))
        self.assertEqual(1, len(reactions[0].targets))
        self.assertEqual(0, reactions[0].sources[0])
        self.assertEqual(1, reactions[0].targets[0])

    def test_delete_items(self):
        api.add_reaction(self.neti, 'AB', [0], [1])

        with self.assertRaises(NodeNotFreeError):
            api.delete_node(self.neti, 0)
        with self.assertRaises(NodeNotFreeError):
            api.delete_node(self.neti, 1)

        api.delete_reaction(self.neti, 0)
        api.delete_node(self.neti, 0)
        api.delete_node(self.neti, 1)
        api.delete_node(self.neti, 2)

        self.assertEqual(list(), api.get_reactions(self.neti))
        self.assertEqual(list(), api.get_nodes(self.neti))

    def test_exceptional_reactions(self):
        with self.assertRaises(ValueError):
            api.add_reaction(self.neti, 'circular', [2], [2])

        with self.assertRaises(ValueError):
            api.add_reaction(self.neti, 'empty_reactants', [], [2])

        with self.assertRaises(ValueError):
            api.add_reaction(self.neti, 'empty_products', [2], [])

    def test_reverse(self):
        api.add_reaction(self.neti, 'AB', [0], [1])
        self.assertTrue(api.is_reactant(self.neti, 0, 0))
        self.assertFalse(api.is_reactant(self.neti, 1, 0))
        self.assertFalse(api.is_product(self.neti, 0, 0))
        self.assertTrue(api.is_product(self.neti, 1, 0))
        self.assertFalse(api.is_reactant(self.neti, 2, 0))
        self.assertFalse(api.is_product(self.neti, 2, 0))

        api.add_reaction(self.neti, 'AC', [0], [2])
        self.assertEqual(api.get_reactions_as_reactant(self.neti, 0), {0, 1})
        self.assertEqual(api.get_reactions_as_product(self.neti, 0), set())
        self.assertEqual(api.get_reactions_as_product(self.neti, 2), {1})

    def test_simple_handles(self):
        """Simple tests for Bezier handles."""
        api.add_reaction(self.neti, 'AB', [0], [1])
        api.set_reaction_center_handle(0, 0, Vec2(-10, 30))
        self.assertEqual(api.get_reaction_center_handle(0, 0), Vec2(-10, 30))

        api.set_reaction_node_handle(0, 0, 0, True, Vec2(40, 50))
        self.assertEqual(api.get_reaction_node_handle(0, 0, 0, True), Vec2(40, 50))

        with self.assertRaises(NodeIndexError):
            api.get_reaction_node_handle(0, 0, 12, True)

        # test for the case where node exists but not reactant/product
        with self.assertRaises(ValueError):
            api.get_reaction_node_handle(0, 0, 1, True)

        with self.assertRaises(ValueError):
            api.get_reaction_node_handle(0, 0, 0, False)

        with self.assertRaises(ReactionIndexError):
            api.get_reaction_node_handle(0, 2, 0, True)