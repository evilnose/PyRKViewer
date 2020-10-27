"""
The color of all selected nodes and reactions are set to the picked color.

Version 0.01: Author: Gary Geng (2020)

"""

# pylint: disable=maybe-no-member
from rkplugin.api import Color
import wx
from typing import List
from rkplugin.plugins import CommandPlugin, PluginMetadata, WindowedPlugin
from rkplugin import api
from rkplugin.events import SelectionDidUpdateEvent


metadata = PluginMetadata(
    name='ColorSelected',
    author='Gary Geng',
    version='0.0.1',
    short_desc='Pick a color, and set everything selected to that color.',
    long_desc='The color of all selected nodes and reactions are set to the picked color.'
)


class ColorSelected(WindowedPlugin):
    def __init__(self):
        super().__init__(metadata)
        self.num_selected = 0
        self.text = None

    def create_window(self, dialog):
        """
        Create the popup window which contains the crucial color picker control.
        """
        # Create top-level window
        window = wx.Window(dialog, size=(300, 400))

        # Create info message
        self.text = wx.StaticText(window)
        self.update_text()

        # Create colorpicker
        picker = wx.ColourPickerCtrl(window)
        picker.Bind(wx.EVT_COLOURPICKER_CHANGED, self.color_callback)

        # Set sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.text, wx.SizerFlags().CenterHorizontal().Border(wx.TOP, 10))
        sizer.Add(picker, wx.SizerFlags().CenterHorizontal().Border(wx.TOP, 10))
        window.SetSizer(sizer)

        return window

    def color_callback(self, evt):
        """
        Callback for the color picker control; sets the color of every node/reaction selected.
        """
        wxcolor = evt.GetColour()
        color = Color.from_rgb(wxcolor.GetRGB())

        # start group action context for undo purposes
        with api.group_action():
            # color selected nodes
            for index in api.selected_node_indices():
                api.update_node(api.cur_net_index(), index, fill_color=color, border_color=color)

            # color selected reactions
            for index in api.selected_reaction_indices():
                api.update_reaction(api.cur_net_index(), index, fill_color=color)

    def on_selection_did_change(self, evt: SelectionDidUpdateEvent):
        """
        Overrides base class event handler to update number of items selected.

        Args:
            self
            node_indices(List[int]): List of node indices changed.
            reaction_indices (List[int]): List of reaction indices changed.
            compartment_indices (List[int]): List of compartment indices changed.
        """
        self.num_selected = len(evt.node_indices) + len(evt.reaction_indices) + len(
            evt.compartment_indices)
        self.update_text()

    def update_text(self):
        """
        Update the information text to report the number of selected (changed) items.
        """
        if self.text is not None:
            self.text.SetLabel('Number of items selected: {}'.format(self.num_selected))
