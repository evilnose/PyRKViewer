
from rkviewer.canvas.geometry import Vec2
from rkviewer.canvas.data import CompositeShape, RectanglePrim
from rkviewer.plugin import api
from test.api.common import DummyAppTest


class TestShapes(DummyAppTest):
    def test_default_shape(self):
        '''Make sure the default shape is a single rectangle primitive'''
        api.add_node(0, 'foo')
        foo = api.get_node_by_index(0, 0)

        self.assertEqual(0, foo.shape_index)
        self.assertTrue(isinstance(foo.shape, CompositeShape))
        self.assertEqual(1, len(foo.shape.items))

        primitive, transform = foo.shape.items[0]
        self.assertTrue(isinstance(primitive, RectanglePrim))
        self.assertEqual(transform.scale, Vec2(1, 1))
        self.assertEqual(transform.translation, Vec2(0, 0))

    def test_set_prop(self):
        api.add_node(0, 'foo')
        api.set_node_shape_property(0, 0, 0, 'fill_color', api.Color(66, 66, 66))

        foo = api.get_node_by_index(0, 0)
        primitive = foo.shape.items[0]
        primitive, _transform = foo.shape.items[0]
        self.assert_(isinstance(primitive, RectanglePrim))
        self.assert_(hasattr(primitive, 'fill_color'))
        self.assertEqual(getattr(primitive, 'fill_color'), api.Color(66, 66, 66))

