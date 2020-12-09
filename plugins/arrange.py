'''
Given some selected nodes, this plugin  will rearrange them in specific ways.

Version 0.01: Author: Carmen Perena Cortes 2020

'''

import wx
from rkplugin.plugins import PluginMetadata, WindowedPlugin, PluginCategory
from rkplugin import api
from rkplugin.api import Node, Vec2, Reaction
import math
from dataclasses import field
from typing import List
import os

metadata = PluginMetadata(
    name='Node Alignment',
    author='Carmen Perena, Herbert M Sauro',
    version='0.0.1',
    short_desc='Rearrange',
    long_desc='Rearrange selected nodes into chosen style',
    category=PluginCategory.UTILITIES,
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
        window = wx.Panel(dialog, pos=(0,0), size=(195, 375))

        top = 10
        left = 10

        path = os.path.realpath(__file__)
        path = os.path.dirname(os.path.abspath(path))
        s = os.path.join (path + '\\alignLeft_XP.bmp')
        bmp = wx.Bitmap(s, wx.BITMAP_TYPE_ANY)
        apply_btn = wx.BitmapButton(window, -1, pos=(left, top), size=(32,32), bitmap=bmp)
        wx.StaticText(window, -1, 'Align Left', (left+40, top+8))
        apply_btn.Bind(wx.EVT_BUTTON, self.AlignLeft)

        top += 35
        s = os.path.join (path + '\\alignRight_XP.bmp')
        bmp = wx.Bitmap(s, wx.BITMAP_TYPE_ANY)
        apply_btn = wx.BitmapButton(window, -1, pos=(left, top), size=(32,32), bitmap=bmp)
        wx.StaticText(window, -1, 'Align Right', (left+40, top+8))
        apply_btn.Bind(wx.EVT_BUTTON, self.AlignRight)

        top += 35
        s = os.path.join (path + '\\alignVertCenter_XP.bmp')
        bmp = wx.Bitmap(s, wx.BITMAP_TYPE_ANY)
        apply_btn = wx.BitmapButton(window, -1, pos=(left, top), size=(32,32), bitmap=bmp)
        wx.StaticText(window, -1, 'Align Center', (left+40, top+8))
        apply_btn.Bind(wx.EVT_BUTTON, self.AlignCenter)

        top += 35
        path = os.path.realpath(__file__)
        path = os.path.dirname(os.path.abspath(path))
        s = os.path.join (path + '\\alignTop_XP.bmp')
        bmp = wx.Bitmap(s, wx.BITMAP_TYPE_ANY)
        apply_btn = wx.BitmapButton(window, -1, pos=(left, top), size=(32,32), bitmap=bmp)
        wx.StaticText(window, -1, 'Align Top', (left+40, top+8))
        apply_btn.Bind(wx.EVT_BUTTON, self.AlignTop)

        top += 35
        s = os.path.join (path + '\\alignBottom_XP.bmp')
        bmp = wx.Bitmap(s, wx.BITMAP_TYPE_ANY)
        apply_btn = wx.BitmapButton(window, -1, pos=(left, top), size=(32,32), bitmap=bmp)
        wx.StaticText(window, -1, 'Align Bottom', (left+40, top+8))
        apply_btn.Bind(wx.EVT_BUTTON, self.AlignBottom)

        top += 35
        s = os.path.join (path + '\\alignHorizCenter_XP.bmp')
        bmp = wx.Bitmap(s, wx.BITMAP_TYPE_ANY)
        apply_btn = wx.BitmapButton(window, -1, pos=(left, top), size=(32,32), bitmap=bmp)
        wx.StaticText(window, -1, 'Align Middle', (left+40, top+8))
        apply_btn.Bind(wx.EVT_BUTTON, self.AlignMiddle)

        top += 35
        s = os.path.join (path + '\\alignOnGrid_XP.bmp')
        bmp = wx.Bitmap(s, wx.BITMAP_TYPE_ANY)
        apply_btn = wx.BitmapButton(window, -1, pos=(left, top), size=(32,32), bitmap=bmp)
        wx.StaticText(window, -1, 'Grid', (left+40, top+8))
        apply_btn.Bind(wx.EVT_BUTTON, self.Grid)

        top += 35
        s = os.path.join (path + '\\alignHorizEqually_XP.bmp')
        bmp = wx.Bitmap(s, wx.BITMAP_TYPE_ANY)
        apply_btn = wx.BitmapButton(window, -1, pos=(left, top), size=(32,32), bitmap=bmp)
        wx.StaticText(window, -1, 'Arrange Horizontally', (left+40, top+8))
        apply_btn.Bind(wx.EVT_BUTTON, self.distributeHorizontally)

        top += 35
        s = os.path.join (path + '\\alignVertEqually_XP.bmp')
        bmp = wx.Bitmap(s, wx.BITMAP_TYPE_ANY)
        apply_btn = wx.BitmapButton(window, -1, pos=(left, top), size=(32,32), bitmap=bmp)
        wx.StaticText(window, -1, 'Arrange Vertically', (left+40, top+8))
        apply_btn.Bind(wx.EVT_BUTTON, self.distributeVertically)

        return window

    def on_did_create_dialog(self):
        # Set position of popup window
        p = api.get_application_position()
        if p.x < 185:
           # Not enough room
           self.dialog.SetPosition ((p.x+200, p.y))
        else:
           self.dialog.SetPosition ((p.x-185, p.y))
    
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

    def findMinY(self, l):
        '''
        Find the left-most node's x position
        Args:
            self
            l: the list of indices of the selected nodes
        '''
        ypos = api.get_node_by_index(0, 0).position.y
        for a in l:
            cur = api.get_node_by_index(0, a)
            newY = cur.position.y
            if(newY < ypos):
                ypos = newY
        return ypos

    def findMaxY(self, l):
        '''
        Find the right-most node's x position
        Args:
            self
            l: the list of indices of the selected nodes
        '''
        ypos = api.get_node_by_index(0, 0).position.y
        for a in l:
                cur = api.get_node_by_index(0, a)
                newY = cur.position.y
                if(newY > ypos):
                    ypos = newY
        return ypos

    def setDefaultHandles(self):
        with api.group_action():
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
            self.setDefaultHandles()

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
            self.setDefaultHandles()

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
            self.setDefaultHandles()

    def Grid(self, evt):
        '''
        Align selected nodes in a net grid manner
        Args:
            self
            evt
        '''
        with api.group_action():
            s = api.get_selected_node_indices(0)
            x = 40
            y = 40
            count = 1
            for a in s:
                api.move_node(0, a, position=Vec2(x, y))
                x = x + 130
                if count % 5 == 0:
                    y = y + 130
                    x = 40
                count = count + 1
            self.setDefaultHandles()              

    def AlignTop(self, evt):
        '''
        Align selected nodes to the left-most node's x position
        Args:
            self
            evt
        '''
        with api.group_action():
            s = api.get_selected_node_indices(0) #TODO: 2 of these
            ypos = self.findMinY(s)
            for a in s:
                cur = api.get_node_by_index(0, a)
                x = cur.position.x
                newPos = Vec2(x, ypos)
                api.move_node(0, a, newPos)
            self.setDefaultHandles()

      
    def AlignBottom(self, evt):
        '''
        Align selected nodes to the right-most node's x position
        Args:
            self
            evt
        '''
        with api.group_action():
            s = api.get_selected_node_indices(0) #TODO: 2 of these
            ypos = self.findMaxY(s)
            for a in s:
                cur = api.get_node_by_index(0, a)
                x = cur.position.x
                newPos = Vec2(x, ypos)
                api.move_node(0, a, newPos)
            self.setDefaultHandles()

    def AlignMiddle(self, evt): # TODO: would the average make more sense?
        '''
        Align selected nodes to the relative center of the x positions of the nodes
        Args:
            self
            evt
        '''
        with api.group_action():
            s = api.get_selected_node_indices(0) #TODO: 2 of these
            yMin = self.findMinY(s)
            yMax = self.findMaxY(s)
            ypos = math.floor((yMax + yMin)/2)
            for a in s:
                cur = api.get_node_by_index(0, a)
                x = cur.position.x
                newPos = Vec2(x, ypos)
                api.move_node(0, a, newPos)
            self.setDefaultHandles()

    def distributeHorizontally(self, evt):
        with api.group_action():
            s = api.get_selected_node_indices(0) #TODO: 2 of these
            yMin = self.findMinY(s)
            yMax = self.findMaxY(s)
            ypos = math.floor((yMax + yMin)/2)
            x = 40
            for a in s:
                newPos = Vec2(x, ypos)
                api.move_node(0, a, newPos)
                x = x + 130
            self.setDefaultHandles()

    def distributeVertically(self, evt):
        with api.group_action():
            s = api.get_selected_node_indices(0) #TODO: 2 of these
            xMin = self.findMinX(s)
            xMax = self.findMaxX(s)
            xpos = math.floor((xMax + xMin)/2)
            y = 40
            for a in s:
                newPos = Vec2(xpos, y)
                api.move_node(0, a, newPos)
                y = y + 130
            self.setDefaultHandles()