"""Configuration parameters.
"""
# pylint: disable=maybe-no-member
from rkviewer.canvas.geometry import Vec2
import wx
import copy


DEFAULT_THEME = {
    'overall_bg': wx.Colour(255, 112, 0),
    'canvas_bg': wx.WHITE,
    'toolbar_bg': wx.Colour(230, 230, 230),
    'canvas_width': 1000,
    'canvas_height': 620,
    'vgap': 2,  # vertical gap between toolbars and canvas
    'hgap': 2,  # horizontal gap between toolbars and canvas
    'canvas_outside_bg': wx.Colour(160, 160, 160),  # Bg color for the parts out of bounds
    'mode_panel_width': 100,
    'toolbar_height': 40,
    'edit_panel_width': 260,
    'node_fill': wx.Colour(150, 255, 150, 200),
    'node_border': wx.Colour(19, 173, 2),
    'node_width': 50,
    'node_height': 30,
    'node_border_width': 2,
    'node_font_size': 10,
    'node_font_color': wx.Colour(255, 0, 0, 100),
    'select_outline_width': 2,  # Width of the outline around each selected node
    'select_outline_padding': 3,  # Padding of the outline around each selected node
     # Color of control handles, e.g. resize handles, Bezier handles
    'handle_color': wx.Colour(0, 140, 255),  
     # Color of control handles when they are highlighted, if applicable
    'highlighted_handle_color': wx.Colour(255, 112, 0),
    'select_box_padding': 5,  # Padding of the select box, relative to the mininum possible bbox
    'select_handle_length': 8,  # Length of the squares one uses to drag resize nodes
    'zoom_slider_bg': wx.Colour(150, 150, 150),
    'drag_fill': wx.Colour(0, 140, 255, 20),
    'drag_border': wx.Colour(0, 140, 255),
    'drag_border_width': 1,
    'react_node_padding': 5,
    'react_node_border_width': 3,
    'reactant_border': wx.Colour(255, 100, 100),
    'product_border': wx.Colour(0, 214, 125),
    'reaction_center_size': 10,
    'reaction_fill': wx.BLACK,
    'reaction_line_thickness': 2,
    'selected_reaction_fill': wx.Colour(0, 140, 255),
    'comp_fill': wx.Colour(158, 169, 255, 200),
    'comp_border': wx.Colour(0, 29, 255),
    'comp_border_width': 2,
}

DEFAULT_ARROW_TIP = [Vec2(1, 15), Vec2(4, 8), Vec2(1, 1), Vec2(21, 8)]

DEFAULT_SETTINGS = {
    'init_zoom': 1,
    'status_fields': [
        ('mode', 100),
        ('cursor', 100),
        ('zoom', 100),
        ('fps', 100),
    ],  # first element: status field identifier; second element: field width
    'decimal_precision': 2,
    'reaction_radius': 6,
    'min_node_width': 20,
    'min_node_height': 15,
    'min_comp_width': 350,
    'min_comp_height': 200,
}


theme = copy.copy(DEFAULT_THEME)
settings = copy.copy(DEFAULT_SETTINGS)
