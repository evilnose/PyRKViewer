# pylint: disable=maybe-no-member
import wx
from typing import List
from rkplugin.plugins import CommandPlugin, PluginMetadata, WindowedPlugin
from rkplugin import api


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
        color = evt.GetColour()

        # start group action context for undo purposes
        with api.group_action():
            # color selected nodes
            for index in api.selected_node_indices():
                api.update_node(api.cur_net_index(), index, fill_color=color, border_color=color)

            # color selected reactions
            for index in api.selected_reaction_indices():
                api.set_reaction_color(api.cur_net_index(), index, color)

    def on_selection_did_change(self, node_indices: List[int], reaction_indices: List[int],
                                compartment_indices: List[int]):
        self.num_selected = len(node_indices) + len(reaction_indices) + len(compartment_indices)
        self.update_text()

    def update_text(self):
        if self.text is not None:
            self.text.SetLabel('Number of items selected: {}'.format(self.num_selected))
