"""
Log events for debugging.

Version 0.01: Author: Gary Geng (2020)
"""

# pylint: disable=maybe-no-member
import wx
import random
from rkplugin.plugins import CommandPlugin, PluginMetadata
from rkplugin import api


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

    def on_did_add_node(self, evt):
        print(evt)

    def run(self):
        """
        Log something.
        """
        api.logger().info('run() called')
