"""
Log events for debugging.

Version 0.01: Author: Gary Geng (2020)
"""
import wx

# pylint: disable=maybe-no-member
from rkviewer.canvas.geometry import Vec2
from rkplugin.plugins import CommandPlugin, PluginMetadata, PluginCategory
from rkplugin import api
from rkplugin.api import Rect, Vec2
from rkplugin.events import DidAddNodeEvent, DidMoveBezierHandleEvent
from rkplugin.canvas import CanvasElement, add_element, draw_rect

metadata = PluginMetadata(
    name='Event logger',
    author='Gary Geng',
    version='0.0.1',
    short_desc='Log events.',
    long_desc='Log all events that are handled by plugins.',
    category=PluginCategory.MISC,
)


class SomeElement(CanvasElement):
    def __init__(self):
        super().__init__(30)

    def do_paint(self, gc: wx.GraphicsContext):
        draw_rect(gc, Rect(Vec2(0, 0), Vec2(100, 100)), fill=wx.BLUE)


class EventLogger(CommandPlugin):
    def __init__(self):
        """
        """
        super().__init__(metadata)

    def on_did_add_node(self, evt: DidAddNodeEvent):
        """Uncomment this line to log add node events."""
        # print(evt)

    def on_did_move_nodes(self, evt):
        pass

    def on_did_move_bezier_handle(self, evt: DidMoveBezierHandleEvent):
        """Uncomment this line to log move Bezier handle events."""
        # print(evt)

    def run(self):
        """
        Log something.
        """
        # api.logger().info('run() called')
        # api.translate_network(0, Vec2(50, 50))
        add_element(0, SomeElement())

