'''
Given some selected nodes, this plugin  will rearrange them in specific ways.

Version 0.01: Author: Carmen Perena Cortes 2020

'''

import wx
from rkplugin.plugins import PluginMetadata, WindowedPlugin
from rkplugin import api
from rkplugin.api import Node, Vec2, Reaction
import math
from dataclasses import field
from typing import List
import os

metadata = PluginMetadata(
    name='Rearrange Selected Nodes',
    author='Carmen Perena, Herbert M Sauro',
    version='0.0.1',
    short_desc='Rearrange',
    long_desc='Rearrange a slected nides into chosen style'
)

class AutoLayout(WindowedPlugin):
    def __init__(self):
        '''
        Initialize the RandomNetwork.

        Args:
            self

        '''
        super().__init__(metadata)

    def create_window(self, dialog):
        '''
        Create a window with several inputs and buttons.
        Args:
            self
            dialog
        '''
        # TODO: k, gravity, useMagnetism, useBoundary, useGrid
        window = wx.Panel(dialog, pos=(5,100), size=(300, 400))

        path = os.path.realpath(__file__)
        path = os.path.dirname(os.path.abspath(path))
        s = os.path.join (path + '\\AlignLeft.png')
        bmp = wx.Bitmap(s, wx.BITMAP_TYPE_ANY)
        apply_btn = wx.BitmapButton(window, -1, pos=(30, 10), size=(60,60), bitmap=bmp)
        wx.StaticText(window, -1, 'Align Left', (100, 40))
        apply_btn.Bind(wx.EVT_BUTTON, self.AlignLeft)

        s = os.path.join (path + '\\AlignLeft.png')
        bmp = wx.Bitmap(s, wx.BITMAP_TYPE_ANY)
        apply_btn = wx.BitmapButton(window, -1, pos=(30, 80), size=(60,60), bitmap=bmp)
        wx.StaticText(window, -1, 'Align Right', (100, 110))
        apply_btn.Bind(wx.EVT_BUTTON, self.AlignRight)

        s = os.path.join (path + '\\AlignLeft.png')
        bmp = wx.Bitmap(s, wx.BITMAP_TYPE_ANY)
        apply_btn = wx.BitmapButton(window, -1, pos=(30, 150), size=(60,60), bitmap=bmp)
        wx.StaticText(window, -1, 'Align Center', (100, 180))
        apply_btn.Bind(wx.EVT_BUTTON, self.AlignCenter)

        s = os.path.join (path + '\\AlignLeft.png')
        bmp = wx.Bitmap(s, wx.BITMAP_TYPE_ANY)
        apply_btn = wx.BitmapButton(window, -1, pos=(30, 220), size=(60,60), bitmap=bmp)
        wx.StaticText(window, -1, 'Grid', (100, 250))
        apply_btn.Bind(wx.EVT_BUTTON, self.Grid)

        window.SetPosition (wx.Point(10,10))
        return window
    
    def findMinX(self, l):
        '''
        Find the left-most node's x position
        Args:
            self
            l: the list of indices of the selected nodes
        '''
        xpos = api.get_node_by_index(0, 0).position.x
        for a in l:
                cur = api.get_node_by_index(0, a)
                newX = cur.position.x
                if(newX < xpos):
                    xpos = newX
        return xpos

    def findMaxX(self, l):
        '''
        Find the right-most node's x position
        Args:
            self
            l: the list of indices of the selected nodes
        '''
        xpos = api.get_node_by_index(0, 0).position.x
        for a in l:
                cur = api.get_node_by_index(0, a)
                newX = cur.position.x
                if(newX > xpos):
                    xpos = newX
        return xpos

    def AlignLeft(self, evt):
        '''
        Align selected nodes to the left-most node's x position
        Args:
            self
            evt
        '''
        with api.group_action():
            s = api.get_selected_node_indices(0) #TODO: 2 of these
            xpos = self.findMinX(s)
            for a in s:
                cur = api.get_node_by_index(0, a)
                y = cur.position.y
                newPos = Vec2(xpos, y)
                api.move_node(0, a, newPos)

      
    def AlignRight(self, evt):
        '''
        Align selected nodes to the right-most node's x position
        Args:
            self
            evt
        '''
        with api.group_action():
            s = api.get_selected_node_indices(0) #TODO: 2 of these
            xpos = self.findMaxX(s)
            for a in s:
                cur = api.get_node_by_index(0, a)
                y = cur.position.y
                newPos = Vec2(xpos, y)
                api.move_node(0, a, newPos)

    def AlignCenter(self, evt): # TODO: would the average make more sense?
        '''
        Align selected nodes to the relative center of the x positions of the nodes
        Args:
            self
            evt
        '''
        with api.group_action():
            s = api.get_selected_node_indices(0) #TODO: 2 of these
            xMin = self.findMinX(s)
            xMax = self.findMaxX(s)
            xpos = math.floor((xMax + xMin)/2)
            for a in s:
                cur = api.get_node_by_index(0, a)
                y = cur.position.y
                newPos = Vec2(xpos, y)
                api.move_node(0, a, newPos)

    def Grid(self, evt):
        '''
        Align selected nodes in a net grid manner
        Args:
            self
            evt
        '''
        s = api.get_selected_node_indices(0)
        x = 40; y = 40; count = 1
        for a in s:
            api.update_node(0, a, position=Vec2(x, y))
            x = x + 200
            if count % 5 == 0:
               y = y + 200
               x = 40
            count = count + 1

        for r in api.get_reactions(0):
            handles = api.default_handle_positions(0, r.index) # centroid, sources, target
            sources = r.sources
            targets = r.targets
            api.set_reaction_center_handle(0, r.index, handles[0])
            count = 1
            for s in sources:
                api.set_reaction_node_handle(0, r.index, s, True, handles[count])
                count += 1
            for t in targets:
                api.set_reaction_node_handle(0, r.index, t, False, handles[count])
                count += 1
