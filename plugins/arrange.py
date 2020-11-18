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
        window = wx.Panel(dialog, pos=(5,100), size=(300, 300))

        import os
        path = os.path.realpath(__file__)
        path = os.path.dirname(os.path.abspath(path))
        s = os.path.join (path + '\\AlignLeft.png')
        bmp = wx.Bitmap(s, wx.BITMAP_TYPE_ANY)
        apply_btn = wx.BitmapButton(window, -1, pos=(30, 10), size=(30,30), bitmap=bmp)
        apply_btn.Bind(wx.EVT_BUTTON, self.AlignLeft)

        apply_btn = wx.Button(window, -1, 'Align Right', (30, 40))
        apply_btn.Bind(wx.EVT_BUTTON, self.AlignRight)

        apply_btn = wx.Button(window, -1, 'Align Center', (30, 70))
        apply_btn.Bind(wx.EVT_BUTTON, self.AlignCenter)

        apply_btn = wx.Button(window, -1, 'Grid', (30, 100))
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
            x = x + 100
            if count % 5 == 0:
               y = y + 100
               x = 40
            count = count + 1
