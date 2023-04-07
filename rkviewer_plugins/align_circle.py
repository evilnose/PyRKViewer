"""
Aligns nodes into circle
Version 1.0.0: Author: Evan Yip and Jin Xu (2021)

"""
import wx
from rkviewer.plugin.classes import PluginMetadata, WindowedPlugin, PluginCategory
from rkviewer.plugin import api
from rkviewer.plugin.api import Vec2
import numpy as np
import math


class AlignCircle(WindowedPlugin):
    metadata = PluginMetadata(
        name='AlignCircle',
        author='Evan Yip and Jin Xu',
        version='1.0.0',
        short_desc='Align Circle',
        long_desc='Aligns the nodes into a circle',
        category=PluginCategory.VISUALIZATION
    )

    def __init__(self):
        """
        Initialize the AlignCircle

        Args:
            self
        """
        # allows the align circle class to inherit
        # the methods of the Windowed Plugin Class
        super().__init__()

    def create_window(self, dialog):
        """
        Create a window to do the structural analysis.
        Args:
            self
            dialog
        """
        # Making the window
        window = wx.Panel(dialog, pos=(5, 100), size=(300, 155))
        wx.StaticText(window, -1, 'Select nodes to arrange in circle',
                      (15, 10))

        # Use default radius
        wx.StaticText(window, -1, 'Use default radius:', (15, 30))
        self.defaultCheck = wx.CheckBox(window, -1, pos=(150, 30))
        self.defaultCheck.SetValue(True)

        # Making radius setable
        wx.StaticText(window, -1, 'Input desired radius:', (15, 55))
        self.radiusText = wx.TextCtrl(window, -1, '0', (150, 55),
                                      size=(120, 22))
        self.radiusText.SetInsertionPoint(0)
        self.radiusText.Bind(wx.EVT_TEXT, self.OnText_radius)  # binding test
        self.radiusValue = float(self.radiusText.GetValue())

        # Making the toggle button
        apply_btn = wx.ToggleButton(window, -1, 'Apply', (100, 85),
                                    size=(80, 22))
        apply_btn.SetValue(False)
        # Binding the method to the button
        apply_btn.Bind(wx.EVT_TOGGLEBUTTON, self.Apply)
        return window

    def find_center(self, num_nodes, nodes):
        """
        Takes in the number of nodes and list of node indices and
        computes the optimal centerpoint for the circle
        Parameters: num_nodes(int) - number of nodes,
            node_indices(list) - list of nodes indices
        Returns: center(tuple)
        """
        # Max dimension of the node size
        max_dim = 0  # will consider this the diameter of a circle node
        for i in nodes:
            # Get node
            node = api.get_node_by_index(0, i)
            for dim in node.size:
                if dim > max_dim:
                    max_dim = dim

        # Approximate circumference estimate
        spacing = max_dim / 4
        circum_estimate = num_nodes * (max_dim + spacing)

        # Computing radius
        r = circum_estimate / (2*np.pi) + max_dim

        center = (r, r)
        return center

    def cart(self, r, theta):
        """
        Converts from polar coordinates to cartesian coordinates
        Parameters: r(double), theta(double in radians)
        Returns: (x,y) cartesian coordinate tuple
        """
        x = r * math.cos(theta)
        y = r * math.sin(theta)
        return x, y

    def get_new_position(self, node_index, r, theta):
        """
        Takes in the node index and outputs the new position for that node
        Parameters: r(double), theta(double in radians)
        Returns: (x,y) cartesian coordinate tuple
        """
        node = api.get_node_by_index(0, node_index)
        size = node.size  # (width, height)
        # accounting for slight offset, converting to cartesian
        nodeCenter = self.cart(r - size[0], theta)
        # accounting for node position being specified by top left corner
        x = r + nodeCenter[0] - size[0]/2
        y = r + nodeCenter[1] + size[1]/2
        return Vec2(x, y)

    def OnText_radius(self, event):
        """
        Catches exception if self.radiusText can not be converted
        to a floating point number. Opens a window.
        """
        update = event.GetString()
        if update != '':
            try:
                self.radiusValue = float(self.radiusText.GetValue())
            except:
                wx.MessageBox("Please enter a floating point number"
                              "for the desired radius", "Message",
                              wx.OK | wx.ICON_INFORMATION)

    def CheckSelection(self, nodes):
        """
        Verifies that there are selected nodes. Raises window if
        no nodes are selected, but apply button is pressed
        """
        if nodes == 0:
            wx.MessageBox("Please select desired nodes to arrange"
                          "in circle", "Message", wx.OK | wx.ICON_INFORMATION)
            return True

    def Apply(self, event):
        """
        If apply button is clicked, the nodes will be arranged in a circle
        using either a default radius or a user input radius.
        """
        def translate_nodes(node_indices, r, phi):
            """
            Takes in list of node indices, desired radius, and phi
            and moves the current node
            to its new position
            """
            # Iterate through the nodes and change their position.
            node_num = 0
            for i in node_ind:
                theta = node_num * phi  # angle position for node
                newPos = self.get_new_position(i, r, theta)
                if newPos[0] < 0 or newPos[1] < 0:
                    wx.MessageBox("Please increase radius size",
                                  "Message", wx.OK | wx.ICON_INFORMATION)
                    return
                api.move_node(0, i, newPos, False)
                node_num += 1  # updating node number

        # Get button and checkbox state
        btn_state = event.GetEventObject().GetValue()
        # chk_state = self.OnDefaultCheck()
        chk_state = self.defaultCheck.GetValue()

        # If the button is pressed, arrange the nodes into a circle
        if btn_state is True:
            # Get number of nodes selected
            node_len = len(api.selected_node_indices())
            # get list of node indices
            node_ind = api.selected_node_indices()

            # If no nodes selected raise error
            select = self.CheckSelection(node_len)
            if select is True:
                return

            # If default radius is checked
            if chk_state is True:
                # Compute the expected center of the circle
                center = self.find_center(node_len, node_ind)
                # Compute the angle step between each node
                phi = 2 * math.pi / node_len
                r = center[0]  # radius
                translate_nodes(node_ind, r, phi)

            else:
                r = self.radiusValue
                center = Vec2(r, r)
                phi = 2 * math.pi / node_len  # angle step between each node
                translate_nodes(node_ind, r, phi)  # translating nodes

            # Making the reactions straight lines
            rxns = api.get_reaction_indices(0)
            for rxn in rxns:
                api.update_reaction(net_index=0, reaction_index=rxn,
                                    use_bezier=False)
            # Setting button state back to False (unclicked)
            event.GetEventObject().SetValue(False)
