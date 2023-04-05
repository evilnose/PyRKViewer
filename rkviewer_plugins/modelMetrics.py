"""
Count the numbers of compartments, nodes and reactions in the model on canvas.
Version 1.0.0: Author: Jin Xu (2023)
"""


# pylint: disable=maybe-no-member
import wx
from rkviewer.plugin.classes import PluginMetadata, CommandPlugin, PluginCategory
from rkviewer.plugin import api


class ModelMetrics(CommandPlugin):
    metadata = PluginMetadata(
        name='ModelMetrics',
        author='Jin Xu',
        version='1.0.0',
        short_desc='Model Metrics.',
        long_desc='Count the numbers of compartments, nodes and reactions in the model on canvas.',
        category=PluginCategory.MODELS
    )

    def run(self):
        """
        Implement the model metrics.
        Args:
            self
        """

        netIn = 0
        numCompartments = api.compartments_count(netIn)
        numNodes = api.node_count(netIn)
        numReactions = api.reaction_count(netIn)

        wx.MessageBox('Number of compartments is %s \nNumber of nodes is %s \nNumber of reactions is %s \n' 
        % (str(numCompartments), str(numNodes), str(numReactions)), "Message", wx.OK | wx.ICON_INFORMATION)




