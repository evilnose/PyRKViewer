"""
Export the network on canvas to an Antimony string.
Version 1.0.0: Author: Jin Xu (2021)
"""


# pylint: disable=maybe-no-member
import wx
from rkviewer.plugin.classes import PluginMetadata, WindowedPlugin, PluginCategory
from rkviewer.plugin import api
from rkviewer.plugin.api import Node, Vec2, Reaction, Color
import os



class ExportAntimony(WindowedPlugin):
    metadata = PluginMetadata(
        name='ExportAntimony',
        author='Jin Xu',
        version='1.0.0',
        short_desc='Export Antimony.',
        long_desc='Export the Antimony String from the network on canvas.',
        category=PluginCategory.MODELS
    )

    def create_window(self, dialog):
        """
        Create a window to do the antimony export.
        Args:
            self
            dialog
        """
        self.window = wx.Panel(dialog, pos=(5,100), size=(300, 320))

        # show_btn = wx.Button(self.window, -1, 'Export', (5, 5))
        # show_btn.Bind(wx.EVT_BUTTON, self.Show)
        export_btn = wx.Button(self.window, -1, 'Export and Save', (5, 5))
        export_btn.Bind(wx.EVT_BUTTON, self.Export)

        copy_btn = wx.Button(self.window, -1, 'Copy To Clipboard', (130, 5))
        copy_btn.Bind(wx.EVT_BUTTON, self.Copy)

        # copy_btn = wx.Button(self.window, -1, 'Copy To Clipboard', (83, 5))
        # copy_btn.Bind(wx.EVT_BUTTON, self.Copy)

        # save_btn = wx.Button(self.window, -1, 'Save', (205, 5))
        # save_btn.Bind(wx.EVT_BUTTON, self.Save)

        wx.StaticText(self.window, -1, 'Antimony string:', (5,30))
        self.antimonyText = wx.TextCtrl(self.window, -1, "", (10, 50), size=(260, 220), style=wx.TE_MULTILINE|wx.HSCROLL)
        self.antimonyText.SetInsertionPoint(0)

        return self.window

    # def Show(self, evt):
    #     """
    #     Handler for the "Export" button.
    #     Get the network on canvas and change it to an Antimony string.
    #     """
    #     isReversible = True
    #     netIn = 0
    #     numNodes = api.node_count(netIn)
        
    #     if numNodes == 0:
    #         wx.MessageBox("Please import a network on canvas", "Message", wx.OK | wx.ICON_INFORMATION)
    #     else:
    #         allNodes = api.get_nodes(netIn)
    #         numReactions = api.reaction_count(netIn)
    #         antStr = ''
    #         allReactions = api.get_reactions(netIn)
    #         for i in range(numReactions):
    #             antStr = antStr + 'J' + str (i) + ': '
    #             rct_num = len(allReactions[i].sources)
    #             prd_num = len(allReactions[i].targets)
    #             for j in range(rct_num-1):
    #                 antStr = antStr + allNodes[allReactions[i].sources[j]].id
    #                 antStr = antStr + ' + '
    #             antStr = antStr + allNodes[allReactions[i].sources[rct_num-1]].id
    #             antStr = antStr + ' -> '
    #             for j in range(prd_num-1):
    #                 antStr = antStr + allNodes[allReactions[i].targets[j]].id
    #                 antStr = antStr + ' + '
    #             antStr = antStr + allNodes[allReactions[i].targets[prd_num-1]].id
    #             antStr = antStr + '; E' + str (i) + '*(k' + str (i) 
    #             for j in range(rct_num):
    #                 antStr = antStr + '*' + allNodes[allReactions[i].sources[j]].id
    #             if isReversible:
    #                 antStr = antStr + ' - k' + str (i) + 'r'
    #                 for j in range(prd_num):
    #                     antStr = antStr + '*' + allNodes[allReactions[i].targets[j]].id
    #             antStr = antStr + ')'
    #             antStr = antStr + ';\n'
    #         self.antimonyText.SetValue(antStr)

    
    def Copy(self, evt):
        """
        Handler for the "Copy" button.
        Copy the Antimony string to a clipboard.
        """
        self.dataObj = wx.TextDataObject()
        self.dataObj.SetText(self.antimonyText.GetValue())
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(self.dataObj)
            wx.TheClipboard.Close()
        else:
            wx.MessageBox("Unable to open the clipboard", "Error")

    def Export(self, evt):
        """
        Handler for the "Export and Save" button.
        Get the network on canvas and change it to an Antimony string.
        Save the Antimony string to a file.
        """
        isReversible = True
        netIn = 0
        numNodes = api.node_count(netIn)
        
        if numNodes == 0:
            wx.MessageBox("Please import a network on canvas", "Message", wx.OK | wx.ICON_INFORMATION)
        else:
            allNodes = api.get_nodes(netIn)
            numReactions = api.reaction_count(netIn)
            antStr = ''
            allReactions = api.get_reactions(netIn)
            for i in range(numReactions):
                antStr = antStr + 'J' + str (i) + ': '
                rct_num = len(allReactions[i].sources)
                prd_num = len(allReactions[i].targets)
                for j in range(rct_num-1):
                    temp_spec_id = allNodes[allReactions[i].sources[j]].id
                    if ' ' in temp_spec_id:
                        temp_spec_id = temp_spec_id.replace(' ', '_')
                    antStr = antStr + temp_spec_id
                    antStr = antStr + ' + '
                temp_spec_id = allNodes[allReactions[i].sources[rct_num-1]].id
                if ' ' in temp_spec_id:
                    temp_spec_id = temp_spec_id.replace(' ', '_')
                antStr = antStr + temp_spec_id
                antStr = antStr + ' -> '
                for j in range(prd_num-1):
                    temp_spec_id = allNodes[allReactions[i].targets[j]].id
                    if ' ' in temp_spec_id:
                        temp_spec_id = temp_spec_id.replace(' ', '_')
                    antStr = antStr + temp_spec_id
                    antStr = antStr + ' + '
                temp_spec_id = allNodes[allReactions[i].targets[prd_num-1]].id
                if ' ' in temp_spec_id:
                    temp_spec_id = temp_spec_id.replace(' ', '_')
                antStr = antStr + temp_spec_id
                antStr = antStr + '; E' + str (i) + '*(k' + str (i) 
                for j in range(rct_num):
                    temp_spec_id = allNodes[allReactions[i].sources[j]].id
                    if ' ' in temp_spec_id:
                        temp_spec_id = temp_spec_id.replace(' ', '_')
                    antStr = antStr + '*' + temp_spec_id
                if isReversible:
                    antStr = antStr + ' - k' + str (i) + 'r'
                    for j in range(prd_num):
                        temp_spec_id = allNodes[allReactions[i].targets[j]].id
                        if ' ' in temp_spec_id:
                            temp_spec_id = temp_spec_id.replace(' ', '_')
                        antStr = antStr + '*' + temp_spec_id
                antStr = antStr + ')'
                antStr = antStr + ';\n'
            self.antimonyText.SetValue(antStr)


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



