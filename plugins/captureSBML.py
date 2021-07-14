'''
Import a directory of SBML and Antimony files, visualize reactions, capture and save images.

Version 0.0.2: Author: Claire Samuels (2021)
'''


from plugins.importSBML import IMPORTSBML
import wx
from rkviewer.plugin.classes import PluginMetadata, WindowedPlugin, PluginCategory
from rkviewer.plugin import api
from rkviewer.plugin.api import Node, Vec2, Reaction, Color
import os
from libsbml import *
import tellurium

class CaptureSBML(WindowedPlugin):
      metadata = PluginMetadata(
        name='CaptureSBML',
        author='Claire Samuels',
        version='0.0.2',
        short_desc='Visualize and capture SBML or Antimony.',
        long_desc='Import a directory of SBML and Antimony files, visualize reactions, capture and save images.',
        category=PluginCategory.ANALYSIS
    )
      def create_window(self, dialog):
        """
        Create a window to export the SBML.
        Args:
            self
            dialog
        """
        # requires importSBML version 0.0.3
        v = IMPORTSBML.metadata.version.split(".")
        importSBMLvers = 0
        for i in range(3):
          importSBMLvers += pow(10,i)*int(v[len(v)-1-i])
        if importSBMLvers < 3:
          self.window = wx.Panel(dialog, pos=(5,100), size=(300, 320))
          txt = wx.StaticText(self.window, -1, "CaptureSBML requires ImportSBML version 0.0.3 or later!", (10,10))
          txt.Wrap(250)
          return self.window

        # import button
        self.window = wx.Panel(dialog, pos=(5,100), size=(300, 320))
        import_btn = wx.Button(self.window, -1, 'Import', (5, 5))
        import_btn.Bind(wx.EVT_BUTTON, self.Import)

        # Directory text:
        self.display_dir = wx.StaticText(self.window, -1, '', (85,10), (180,25),
                                         style= wx.ST_NO_AUTORESIZE | wx.ST_ELLIPSIZE_START)

        # files to import
        wx.StaticText(self.window, -1, 'Files to Display:', (5,30))
        self.selectedFiles = wx.TextCtrl(self.window, -1, "", (10,50), (240, 150),
                                         style=wx.TE_MULTILINE | wx.TE_READONLY)

        # directory to save images to
        output_dir_label = wx.StaticText(self.window, -1, "Output Directory:", (5,215))
        self.output_dir = wx.TextCtrl(self.window, -1, "", (100,210), (180,25))

        # go button
        go_btn = wx.Button(self.window, -1, 'Go', (200,250))
        go_btn.Bind(wx.EVT_BUTTON, self.Go)

        return self.window

      def Import(self, evt):
        '''
        Handler for "Import" button
        Choose a directory to iterate through'''
        self.dirname = ""
        dlg = wx.DirDialog(self.window, "Choose a directory", self.dirname,
                            wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        self.file_list = []
        if dlg.ShowModal() == wx.ID_OK:
            self.dirname = dlg.GetPath()
            for file in os.listdir(self.dirname):
              # only want .xml files and .ant
              filename = os.fsdecode(file)
              if filename.endswith(".xml") | filename.endswith(".ant"):
                self.file_list.append(filename)
        self.display_dir.SetLabel(str(self.dirname))
        self.selectedFiles.SetLabel(str(self.file_list))

        self.output_dir.Clear()
        self.output_dir.write('{}\\reaction_visualizations'.format(self.dirname))
        dlg.Destroy()

      def Go(self, evt):
        '''
        Handler for "Go" button.
        Reads each file in selected directory. If readable SBML, displays on canvas'''
        reader = SBMLReader()

        self.output_dir_path = self.output_dir.Value
        if not os.path.isdir(self.output_dir_path):
          os.mkdir(self.output_dir_path)
        else:
          dir_cnt = 1
          while os.path.isdir('{} ({})'.format(self.output_dir_path, dir_cnt)):
            dir_cnt += 1
          self.output_dir_path = '{} ({})'.format(self.output_dir_path, dir_cnt)
          os.mkdir(self.output_dir_path)

        self.blank_canvas = []

        for filename in self.file_list:

          f = open(os.path.join(self.dirname, filename), 'r')
          sbmlStr = f.read()

          # convert .ant files to .xml
          if filename.endswith(".ant"):
            try:
              sbmlStr = tellurium.tellurium.antimonyToSBML(sbmlStr)
            except:
              pass

          doc = reader.readSBMLFromString(sbmlStr)
          if doc.getNumErrors() > 0:
            self.blank_canvas.append(filename)
          else:
            try:
              IMPORTSBML.DisplayModel(self, sbmlStr, False, True)
            except ValueError:
              pass
            self.Capture(filename)
        if len(self.blank_canvas) > 0:
          flist = ""
          for blkf in self.blank_canvas:
            flist += blkf + ", "
          flist = flist[:-2]
          wx.MessageBox("Done. Images saved to\n{}\nWarning: No node or reaction information found for {}.\nNo visualizations saved for these files.".format(self.output_dir_path, flist),
                         "Message", wx.OK | wx.ICON_INFORMATION)
        else:
          wx.MessageBox("Done. Images saved to\n{}".format(self.output_dir_path), "Message",
                         wx.OK | wx.ICON_INFORMATION)

      def Capture(self, filename):
        '''
        Saves a png of the current canvas to the chosen output directory
        Args:
          self
          filename: name of sbml file currently displayed'''

        # ensure that the canvas isn't blank
        if api.node_count(0) == 0 and api.reaction_count(0) == 0 and api.compartments_count(0) <= 1:
          self.blank_canvas.append(filename)
        else:
          pathname = os.path.join(self.output_dir_path, 'img_{}.png'.format(filename))

          canv = api.get_canvas()
          img = canv.DrawActiveRectToImage()

          img.SaveFile(pathname)