"""
Export the network on canvas to an Antimony string.
Version 0.01: Author: Jin Xu (2021)
"""


# pylint: disable=maybe-no-member
import wx
from rkplugin.plugins import PluginMetadata, WindowedPlugin, PluginCategory
from rkplugin import api
from rkplugin.api import Node, Vec2, Reaction, Color
import os



class ExportAntimony(WindowedPlugin):
    metadata = PluginMetadata(
        name='ExportAntimony',
        author='Jin Xu',
        version='0.0.1',
        short_desc='Export Antimony.',
        long_desc='Export the Antimony String from the network on canvas.',
        category=PluginCategory.ANALYSIS
    )
    def __init__(self):
        """
        Initialize the ExportAntimony Plugin.
        Args:
            self
        """
        
        super().__init__(metadata)


    def create_window(self, dialog):
        """
        Create a window to do the antimony export.
        Args:
            self
            dialog
        """
        self.window = wx.Panel(dialog, pos=(5,100), size=(300, 320))

        export_btn = wx.Button(self.window, -1, 'Export', (5, 5))
        export_btn.Bind(wx.EVT_BUTTON, self.Export)

        save_btn = wx.Button(self.window, -1, 'Save', (100, 5))
        save_btn.Bind(wx.EVT_BUTTON, self.Save)

        wx.StaticText(self.window, -1, 'Antimony string:', (5,30))
        self.antimonyText = wx.TextCtrl(self.window, -1, "", (10, 50), size=(260, 220), style=wx.TE_MULTILINE)
        self.antimonyText.SetInsertionPoint(0)

        return self.window

    def Export(self, evt):
        """
        Handler for the "Export" button.
        Get the network on canvas and change it to an Antimony string.
        """
        isReversible = True
        netIn = 0
        numNodes = api.node_count(netIn)
        
        if numNodes == 0:
            wx.MessageBox("Please import a network on canvas", "Message", wx.OK | wx.ICON_INFORMATION)
        else:
            allNodes = api.get_nodes(netIn)
            id = allNodes[0].id[0:-2]
            numReactions = api.reaction_count(netIn)
            antStr = ''
            allReactions = api.get_reactions(netIn)
            for i in range(numReactions):
                antStr = antStr + 'J' + str (i) + ': '
                rct_num = len(allReactions[i].sources)
                prd_num = len(allReactions[i].targets)
                for j in range(rct_num-1):
                    antStr = antStr + id + '_' + str (allReactions[i].sources[j])
                    antStr = antStr + ' + '
                antStr = antStr + id + '_' + str (allReactions[i].sources[rct_num-1])
                antStr = antStr + ' -> '
                for j in range(prd_num-1):
                    antStr = antStr + id + '_' + str (allReactions[i].targets[j])
                    antStr = antStr + ' + '
                antStr = antStr + id + '_' + str (allReactions[i].targets[prd_num-1])
                antStr = antStr + '; E' + str (i) + '*(k' + str (i) 
                for j in range(rct_num):
                    antStr = antStr + '*' + id + '_' + str (allReactions[i].sources[j])
                if isReversible:
                    antStr = antStr + ' - k' + str (i) + 'r'
                    for j in range(prd_num):
                        antStr = antStr + '*' + id + '_' + str (allReactions[i].targets[j])
                antStr = antStr + ')'
                antStr = antStr + ';\n'
            self.antimonyText.SetValue(antStr)

    def Save(self, evt):
        """
        Handler for the "Save" button.
        Save the Antimony string to a file.
        """

        self.dirname=""  #set directory name to blank
 
        dlg = wx.FileDialog(self.window, "Save As", self.dirname, wildcard="Antimony files (*.ant)|*.ant", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            # Grab the content to be saved
            itcontains = self.antimonyText.GetValue()
            # Open the file for write, write, close
            self.filename=dlg.GetFilename()
            self.dirname=dlg.GetDirectory()
            filehandle=open(os.path.join(self.dirname, self.filename),'w')
            filehandle.write(itcontains)
            filehandle.close()
        # Get rid of the dialog to keep things tidy
        dlg.Destroy()



