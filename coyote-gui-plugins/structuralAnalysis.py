"""
Do the structural analysis.
Version 0.01: Author: Jin Xu (2020)
"""


# pylint: disable=maybe-no-member
import wx
import wx.grid as  gridlib
from rkviewer.plugin.classes import PluginMetadata, WindowedPlugin, PluginCategory
from rkviewer.plugin import api
from rkviewer.plugin.api import Node, Vec2, Reaction, Color
import math
import random as _random
import numpy as _np
import copy as _copy
from dataclasses import dataclass

class TabOne(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.EXPAND|wx.ALL)
        self.grid_st = gridlib.Grid(self)
        self.grid_st.CreateGrid(20,20)
        for i in range(20):
            self.grid_st.SetColLabelValue(i, "")
        for i in range(20):
            self.grid_st.SetRowLabelValue(i, "")

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.grid_st, 1, wx.EXPAND)
        self.SetSizer(sizer)

class TabTwo(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.EXPAND|wx.ALL)
        self.grid_moi = gridlib.Grid(self)
        self.grid_moi.CreateGrid(20,20)
        for i in range(20):
            self.grid_moi.SetColLabelValue(i, "")
        for i in range(20): 
            self.grid_moi.SetRowLabelValue(i, "")

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.grid_moi, 1, wx.EXPAND)
        self.SetSizer(sizer)

class StructuralAnalysis(WindowedPlugin):
    metadata = PluginMetadata(
        name='StructuralAnalysis',
        author='Jin Xu',
        version='0.0.1',
        short_desc='Structural Analysis.',
        long_desc='StructuralAnalysis Plugin is to calculate and visualize the stoichiometry matrix and conserved moieties for the network.',
        category=PluginCategory.ANALYSIS
    )
    def __init__(self):
        """
        Initialize the StructuralAnalysis Plugin.
        Args:
            self
        """
        super().__init__()
        self.index_list=[]


    def create_window(self, dialog):
        """
        Create a window to do the structural analysis.
        Args:
            self
            dialog
        """
        topPanel = wx.Panel(dialog, pos=(0,0), size=(700, 500))

        # Create two panels size by side
        panel1 = wx.Panel(topPanel, -1, pos=(0,100), size=(200,100))
        panel2 = wx.Panel(topPanel, -1, pos=(100,100),size=(450,100))

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(panel1,0,wx.EXPAND|wx.ALL,border=10)
        sizer.Add(panel2,0,wx.EXPAND|wx.ALL,border=10)
        
        topPanel.SetSizer(sizer)

        # Add a notebook to the second panel
        nb = wx.Notebook(panel2)

        # Create the tabs
        self.tab1 = TabOne(nb)
        self.tab2 = TabTwo(nb)
        nb.AddPage(self.tab1, "Stoichiometry Matrix")
        nb.AddPage(self.tab2, "Conservation Matrix")

        # Make sure the second panel fills the right side. 
        sizer = wx.BoxSizer()
        sizer.Add(nb, 1, wx.EXPAND)
        panel2.SetSizer(sizer)
      
        Compute_btn = wx.Button(panel1, -1, 'Compute Matrix', (20,20))
        Compute_btn.Bind(wx.EVT_BUTTON, self.Compute)

        wx.StaticText(panel1, -1, 'Select a row from the table of', (20,100))
        wx.StaticText(panel1, -1, 'Moiety Conservation Laws', (20,120))
        wx.StaticText(panel1, -1, 'and pick a color:', (20,140))

        Picker = wx.ColourPickerCtrl(panel1, pos=(20,160))
        Picker.Bind(wx.EVT_COLOURPICKER_CHANGED, self.color_callback)

        wx.StaticText(panel1, -1, 'Unhighlight the nodes:', (20,240))
        Clear_Btn = wx.Button(panel1, -1, 'Clear', (20,260))
        Clear_Btn.Bind(wx.EVT_BUTTON, self.unhighlight)

        return topPanel

    def on_did_create_dialog(self):
        # Set position of popup window to top-left corner of screen
        self.dialog.SetPosition((240, 250))


    def Compute(self, evt):
        """
        Handler for the "Compute" button.
        Get the network on canvas.
        Calculate the Stoichiometry Matrix and Conservation Matrix for the randon network.
        """
        def nullspace(A, atol=1e-13, rtol=0):  
            A = _np.atleast_2d(A)
            u, s, vh = _np.linalg.svd(A)
            tol = max(atol, rtol * s[0])
            nnz = (s >= tol).sum()
            ns = vh[nnz:].conj().T
            return ns

        #https://gist.github.com/sgsfak/77a1c08ac8a9b0af77393b24e44c9547
        def rref(B, tol=1e-8, debug=False):
          A = B.copy()
          rows, cols = A.shape
          r = 0
          pivots_pos = []
          row_exchanges = _np.arange(rows)
          for c in range(cols):
            if debug: print ("Now at row", r, "and col", c, "with matrix:"); print (A)
        
            ## Find the pivot row:
            pivot = _np.argmax (_np.abs (A[r:rows,c])) + r
            m = _np.abs(A[pivot, c])
            if debug: print ("Found pivot", m, "in row", pivot)
            if m <= tol:
              ## Skip column c, making sure the approximately zero terms are
              ## actually zero.
              A[r:rows, c] = _np.zeros(rows-r)
              if debug: print ("All elements at and below (", r, ",", c, ") are zero.. moving on..")
            else:
              ## keep track of bound variables
              pivots_pos.append((r,c))
        
              if pivot != r:
                ## Swap current row and pivot row
                A[[pivot, r], c:cols] = A[[r, pivot], c:cols]
                row_exchanges[[pivot,r]] = row_exchanges[[r,pivot]]
                
                if debug: print ("Swap row", r, "with row", pivot, "Now:"); print (A)
        
              ## Normalize pivot row
              A[r, c:cols] = A[r, c:cols] / A[r, c];
        
              ## Eliminate the current column
              v = A[r, c:cols]
              ## Above (before row r):
              if r > 0:
                ridx_above = _np.arange(r)
                A[ridx_above, c:cols] = A[ridx_above, c:cols] - _np.outer(v, A[ridx_above, c]).T
                if debug: print ("Elimination above performed:"); print (A)
              ## Below (after row r):
              if r < rows-1:
                ridx_below = _np.arange(r+1,rows)
                A[ridx_below, c:cols] = A[ridx_below, c:cols] - _np.outer(v, A[ridx_below, c]).T
                if debug: print ("Elimination below performed:"); print (A)
              r += 1
            ## Check if done
            if r == rows:
              break;
          return (A, pivots_pos, row_exchanges)


        netIn = 0
        numNodes = api.node_count(netIn)
        
        if numNodes == 0:
            wx.MessageBox("Please import a network on canvas", "Message", wx.OK | wx.ICON_INFORMATION)
        else:
            allNodes = api.get_nodes(netIn)
            #id = allNodes[0].id[0:-2]
            node =  allNodes[0]
            try:
                primitive, transform = node.shape.items[0]
                self.default_color = primitive.fill_color
            except:
                self.default_color = api.Color(255, 204, 153) #random network node color

            largest_node_index = 0
            for i in range(numNodes):
                if allNodes[i].index > largest_node_index:
                    largest_node_index = allNodes[i].index
            row = largest_node_index + 1
            numReactions = api.reaction_count(netIn)
            #print("numReactions:", numReactions)
            col = numReactions
            self.st = _np.zeros((row, col))
            allReactions = api.get_reactions(netIn)
            for i in range(numReactions):
                for j in range(len(allReactions[i].sources)):
                    #print(allReactions[i].sources[j])
                    for m in range(row):
                        if allReactions[i].sources[j] == m:
                            self.st.itemset((m, i), -1)
                for j in range(len(allReactions[i].targets)):
                    #print(allReactions[i].targets[j])
                    for m in range(row):
                        if allReactions[i].targets[j] == m:
                            self.st.itemset((m,i), 1)


            stt = _np.transpose (self.st)
            m = _np.transpose (nullspace (stt))
            moi_mat = rref(m)[0]

            # set all the values of non-existing nodes to zero
            for i in range(moi_mat.shape[0]):
                for j in range(moi_mat.shape[1]):
                    if _np.array_equal(self.st[j,:], _np.zeros(self.st.shape[1])):
                        moi_mat.itemset((i,j), 0.)

            for i in range(self.st.shape[1]):
                self.tab1.grid_st.SetColLabelValue(i, "J" + str(i))
            for i in range(self.st.shape[0]):
                #self.tab1.grid_st.SetRowLabelValue(i, id + "_" + str(i))
                id = allNodes[i].id
                self.tab1.grid_st.SetRowLabelValue(i, id)
            
            for row in range(self.st.shape[0]):
                for col in range(self.st.shape[1]):
                    self.tab1.grid_st.SetCellValue(row, col,"%d" % self.st.item(row,col))

            for i in range(moi_mat.shape[1]):
                #self.tab2.grid_moi.SetColLabelValue(i, id + "_" + str(i))
                id = allNodes[i].id
                self.tab2.grid_moi.SetColLabelValue(i, id)

            CSUM_id = 0

            for i in range(moi_mat.shape[0]):
                a = moi_mat[i,:]
                a = [0. if abs(a_) < 0.005 else a_ for a_ in a] # some elements are very small
                if _np.array_equal(a, _np.zeros(moi_mat.shape[1])): # delete the row if all the elements are zero
                    CSUM_id = CSUM_id
                else:
                    self.tab2.grid_moi.SetRowLabelValue(CSUM_id, "CSUM" + str(CSUM_id))    

                    for j in range(moi_mat.shape[1]):
                        #self.tab2.grid_moi.SetCellValue(CSUM_id, j, format (moi_mat[i][j], ".2f"))
                        self.tab2.grid_moi.SetCellValue(CSUM_id, j, format (a[j], ".2f")) 
                    CSUM_id += 1 


    def printSelectedCells(self, top_left, bottom_right):
        """
        Based on code from http://ginstrom.com/scribbles/2008/09/07/getting-the-selected-cells-from-a-wxpython-grid/
        """
        cells = []
        
        rows_start = top_left[0]
        rows_end = bottom_right[0]
        cols_start = top_left[1]
        cols_end = bottom_right[1]
        rows = range(rows_start, rows_end+1)
        cols = range(cols_start, cols_end+1)
        cells.extend([(row, col)
            for row in rows
            for col in cols])
            
        self.index_list = []
        for cell in cells:
            row, col = cell
            value = self.tab2.grid_moi.GetCellValue(row,col)
            if value != "0.00" and value != "+0.00" and value != "-0.00" and value !="":
                self.index_list.append(int(col))
            #print("selected nodes:", self.index_list)


    def color_callback(self, evt):
                   
        """
        Get whatever cells are currently selected
        """

        cells = self.tab2.grid_moi.GetSelectedCells()
        if not cells:
            if self.tab2.grid_moi.GetSelectionBlockTopLeft():
                top_left = self.tab2.grid_moi.GetSelectionBlockTopLeft()[0]
                bottom_right = self.tab2.grid_moi.GetSelectionBlockBottomRight()[0]
                self.printSelectedCells(top_left, bottom_right)
            #else:
            #    print (self.currentlySelectedCell)
        else:
            print("no cells are selected")

        
        """
        Callback for the color picker control; sets the color of every node/reaction selected.
        """

        wxcolor = evt.GetColour()
        color = Color.from_rgb(wxcolor.GetRGB())

        # start group action context for undo purposes
        with api.group_action():
            # color selected nodes
            #for index in api.selected_node_indices():

            if len(self.index_list) == 0:
                wx.MessageBox("Please select a row and pick a color again", "Message", wx.OK | wx.ICON_INFORMATION)
            try:
                for index in self.index_list:
                    #api.update_node(api.cur_net_index(), index, fill_color=color, forder_color=color)
                    api.update_node(api.cur_net_index(), index, fill_color=color)
            except:
                wx.MessageBox("Please select a row and pick a color again", "Message", wx.OK | wx.ICON_INFORMATION)


    def unhighlight(self, evt):

        """
        Callback for the color picker control; sets the color of every node/reaction selected.
        """
        
        # start group action context for undo purposes
        with api.group_action():
            # color selected nodes
            #for index in api.selected_node_indices():
            try:
                for index in self.index_list:
                    api.update_node(api.cur_net_index(), index, fill_color=self.default_color)
            except:
                wx.MessageBox("There is no highlighted nodes", "Message", wx.OK | wx.ICON_INFORMATION)


