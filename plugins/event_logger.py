"""
Log events for debugging.

Version 0.01: Author: Gary Geng (2020)
"""

# pylint: disable=maybe-no-member
from rkplugin.plugins import CommandPlugin, PluginMetadata
from rkplugin import api
from rkplugin.events import DidAddNodeEvent, DidMoveBezierHandleEvent

metadata = PluginMetadata(
    name='Event logger',
    author='Gary Geng',
    version='0.0.1',
    short_desc='Log events.',
    long_desc='Log all events that are handled by plugins.'
)


class EventLogger(CommandPlugin):
    def __init__(self):
        """
        """
        super().__init__(metadata)

    def on_did_add_node(self, evt: DidAddNodeEvent):
        print(evt)

    def on_did_move_bezier_handle(self, evt: DidMoveBezierHandleEvent):
        print(evt)

    def run(self):
        """
        Log something.
        """
        api.logger().info('run() called')
