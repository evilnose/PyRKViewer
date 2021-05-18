

from rkviewer.mvc import CompartmentIndexError
from rkviewer.plugin import api
from test.api.common import DummyAppTest


class TestCompartment(DummyAppTest):
    def setUp(self):
        api.add_node(self.neti, 'Alice')
        api.add_node(self.neti, 'Bob')
        api.add_node(self.neti, 'Charlie')

    def test_simple_compartments(self):
        self.assertEqual(api.get_nodes_in_compartment(self.neti, -1), [0, 1, 2])
        api.add_compartment(self.neti, id="c_1")
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