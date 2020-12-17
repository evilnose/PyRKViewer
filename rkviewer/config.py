"""Configuration parameters.
"""
# pylint: disable=maybe-no-member
from typing import Any
from commentjson.commentjson import JSONLibraryException
from rkviewer.utils import get_local_path
import wx
import os
from marshmallow import Schema, fields, validate, missing as missing_, ValidationError
from rkviewer.canvas.geometry import Vec2
import copy
import commentjson
from pathlib import Path


# TODO rename get_local_path
config_dir = "" #get_local_path('.rkviewer')  # This will be set by either appsettings (see below) or CreateConfigDir in view.poy
#settings_theme_path = os.path.join(config_dir, 'settings.json')
#default_settings_path = os.path.join(config_dir, '.default-settings.json')


def GetConfigDir ():
    global config_dir
    return config_dir


def GetThemeSettingsPath ():
    return os.path.join(config_dir, 'settings.json')


# Application based settings stored in an ini file
class AppSettings:

   # Default positions

   def __init__(self):
       self.position = wx.Point (0,0)
       self.size = wx.Size (1366,737)
       self.displaySize = wx.DisplaySize() 
       # Find the center poistion of the frame
       self.position.x = self.displaySize[0] / 2 - self.size.x / 2
       self.position.y = self.displaySize[1] / 2 - self.size.y / 2

   def load_appSettings(self):
       sp = wx.StandardPaths.Get()
       configDir = sp.GetUserConfigDir()
       if not os.path.exists(os.path.join(configDir, 'rkViewer')):
            os.mkdir(os.path.join(configDir, 'rkViewer'))
       fileName = os.path.join(configDir, 'rkViewer', 'appSettings.ini')
       if not os.path.exists (fileName):
          # leave with defaults intact.  
          return 
        
       config = wx.FileConfig(localFilename=fileName) 
       config.SetPath ('PositionAndSize')
       self.position.x = config.ReadInt ('frame_position_x', self.position.x)       
       self.position.y = config.ReadInt ('frame_position_y', self.position.y)       
       self.size.x = config.ReadInt ('frame_size_w', self.size.x)       
       self.size.y = config.ReadInt ('frame_size_h', self.size.y)       

   def save_appSettings(self):
       sp = wx.StandardPaths.Get()
       config_dir = sp.GetUserConfigDir()
       if not os.path.exists(os.path.join(config_dir, 'rkViewer')):
            os.mkdir(os.path.join(config_dir, 'rkViewer'))
       fileName = os.path.join(config_dir, 'rkViewer', 'appSettings.ini')
       if os.path.exists(fileName):
           os.remove (fileName)

       config = wx.FileConfig(localFilename=fileName) 
       config.SetPath ('PositionAndSize')
       config.WriteInt ('frame_position_x', self.position.x)
       config.WriteInt ('frame_position_y', self.position.y)
       config.WriteInt ('frame_size_w', self.size.x)
       config.WriteInt ('frame_size_h', self.size.y)


# TODO merge these schema with those in iodine?
class Color(fields.Field):
    """Field that represents an RGBA color.
    
    To represent the color red, you would write:
    >>> { "some_color": [255, 0, 0] }

    You may also specify its opacity. To make the color red half transparent:
    >>> { "some": [255, 0, 0, 127] }

    In short, you may specify four integer arguments RGBA in an array, which the alpha value
    being optional and defaulting to 255, or fully opaque. Each value must be in range [0, 255].
    """
    list_field = fields.List(fields.Int(), validate=validate.Length(min=3, max=4))
    range_validate = validate.Range(min=0, max=255, error='RGBA values must be between 0 and 255.')

    def __init__(self, **kw):
        super().__init__(**kw)

    def _serialize(self, value: wx.Colour, attr, obj, **kwargs):
        ret = [value.Red(), value.Green(), value.Blue()]
        if value.Alpha() != 255:
            ret += [value.Alpha()]
        return ret

    def _deserialize(self, value, attr, data, **kwargs):
        self.list_field.validate(value)
        for val in value:
            Color.range_validate(val)
        return wx.Colour(*value)


class Pixel(fields.Int):
    """Field that represents some length in pixels.

    The only current restriction is that this must be a nonnegative integer, or
    >>> { "some_width": 23 }
    """
    def __init__(self, **kwargs):
        super().__init__(validate=validate.Range(min=0), **kwargs)


class Dim(fields.Float):
    """Field that represents some real dimension (length)."""

    def __init__(self, **kwargs):
        # TODO should we allow 0? Also decide for pixel
        super().__init__(validate=validate.Range(min=0), **kwargs)


class ThemeSchema(Schema):
    """Schema for the overall theme, i.e. appearance, of the application.

    Attributes:
        overall_bg: Overall background color of the application.
        canvas_bg: Background color of the canvas.
        toolbar_bg: Background color of the toolbar.
        canvas_width: Starting (and minimum) width of the canvas.
        canvas_height: Starting (and minimum) height of the canvas.
        vgap: Vertical gap between toolbars and canvas.
        hgap: Horizontal gap between toolbars and canvas.
        canvas_outside_bg: Background color of the part outside of the bounds of canvas.
        mode_panel_width: Width of the mode selection panel.
        node_fill: Default node fill color.
        node_border: Default node border color.
        node_width: Default node width.
        node_height: Default node height.
        node_border_width: Default node border width.
        node_font_size: Default font size of the node.
        node_font_color: Default font color of the node.
        select_outline_width: Width of the selection outlines (i.e. outline around each selected
                              item).
        select_outline_padding: Padding of the selection outlines.
        handle_color: Color of the Reaction Bezier curves.
        highlighted_handle_color: Color of the Reaction Bezier curves when the cursor hovers over it
        select_box_padding: Padding of the selection rectangle (i.e. the large rectangle that
                            encompasses all the selected items).
        select_handle_length: Side length of the squares one uses to resize nodes/compartments.
        zoom_slider_bg: Background color of the zoom slider.
        drag_fill: The fill color of the drag selection rectangle.
        drag_border: The border color of the drag selection rectangle.
        drag_border_width: The border width of the drag selection rectangle.
        react_node_padding: The outline padding for nodes prepped as reactants or products.
        react_node_border_width: The border width for nodes prepped as reactants or products.
        reactant_border: The outline color for nodes prepped as reactants.
        product_border: The outline color for nodes prepped as products.
        reaction_fill: The default fill color of reaction curves.
        reaction_line_thickness: The default thickness of reaction curves.
        selected_reaction_fill: The fill color of selected reaction curves.
        comp_fill: The default fill color of compartments.
        comp_border: The default border color of compartments.
        comp_border_width: The default border width of compartments.
        reaction_radius: The radius of the reaction centroid circles.

    TODO more documentation under attributes and link to this document in Help or settings.json
    """
    # overall background of the application 
    overall_bg = Color(missing=wx.Colour(240, 240, 240))
    canvas_bg = Color(missing=wx.Colour(255, 255, 255))
    toolbar_bg = Color(missing=wx.Colour(230, 230, 230))
    canvas_width = Pixel(missing=1000)
    canvas_height = Pixel(missing=620)
    # vertical gap between toolbars and canvas
    vgap = Pixel(missing=2)
    # horizontal gap between toolbars and canvas
    hgap = Pixel(missing=2)
    canvas_outside_bg = Color(missing=wx.Colour(160, 160, 160))
    mode_panel_width = Pixel(missing=100)
    toolbar_height = Pixel(missing=75)
    edit_panel_width = Pixel(missing=260)
    node_fill = Color(missing=wx.Colour(255, 204, 153, 200))
    node_border = Color(missing=wx.Colour(255, 108, 9))
    node_width = Dim(missing=50)
    node_height = Dim(missing=30)
    node_corner_radius = Pixel(missing=6)
    node_border_width = Pixel(missing=2)
    node_font_size = Pixel(missing=10)
    node_font_color = Color(missing=wx.Colour(255, 0, 0, 100))
    # Width of the outline around each selected node
    select_outline_width = Pixel(missing=2)
    # Padding of the outline around each selected node
    select_outline_padding = Pixel(missing=3)
    # Color of control handles, e.g. resize handles, Bezier handles
    handle_color = Color(missing=wx.Colour(0, 140, 255))
    # Color of control handles when they are highlighted, if applicable
    highlighted_handle_color = Color(missing=wx.Colour(128, 198, 255))
    # Padding of the select box, relative to the mininum possible bbox
    select_box_padding = Pixel(missing=5)
    # Length of the squares one uses to drag resize nodes
    select_handle_length = Pixel(missing=8)
    zoom_slider_bg = Color(missing=wx.Colour(180, 180, 180))
    drag_fill = Color(missing=wx.Colour(0, 140, 255, 20))
    drag_border = Color(missing=wx.Colour(0, 140, 255))
    drag_border_width = Pixel(missing=1)
    react_node_padding = Pixel(missing=5)
    react_node_border_width = Pixel(missing=3)
    reactant_border = Color(missing=wx.Colour(255, 100, 100))
    product_border = Color(missing=wx.Colour(0, 214, 125))
    reaction_fill = Color(missing=wx.Colour(91, 176, 253))
    reaction_line_thickness = Dim(missing=2)
    selected_reaction_fill = Color(missing=wx.Colour(0, 140, 255))
    comp_fill = Color(missing=wx.Colour(158, 169, 255, 200))
    comp_border = Color(missing=wx.Colour(0, 29, 255))
    comp_border_width = Dim(missing=2)
    comp_corner_radius = Dim(missing=6)
    reaction_radius = Dim(missing=6)
    modifier_line_color = Color(missing=wx.Colour(202, 148, 255))
    modifier_line_width = Dim(missing=2)


class RootSchema(Schema):
    """The overall root schema.
    
    Attributes:
        theme: The theme settings (i.e. colors and dimensions) of the application.
    """
    theme = fields.Nested(ThemeSchema, missing=ThemeSchema().load({}))


# TODO put this in the schema somewhere
DEFAULT_ARROW_TIP = [Vec2(1, 15), Vec2(4, 8), Vec2(1, 1), Vec2(21, 8)]


# These settings are not meant to be modifiable by the user
BUILTIN_SETTINGS = {
    "init_zoom": 1,
    "status_fields": [
        ("mode", 100),
        ("cursor", 100),
        ("zoom", 100),
        ("fps", 100),
    ],  # first element: status field identifier; second element: field width
    "decimal_precision": 2,
    "min_node_width": 20,
    "min_node_height": 15,
    "min_comp_width": 350,
    "min_comp_height": 200,
}


INIT_SETTING_TEXT = '''// settings.json auto-generated by RKViewer.
// Edit this file to override default application settings.
// After you have finished editing, click File > Reload Settings to load the new settings.
// Note that some settings may not take effect until the application is restarted.
{
    // Theme and appearance settings
    "theme": {

    }
}

'''


DEFAULT_SETTING_FMT = '''// default-settings.json auto-generated by RKViewer.
// Note that you should *not* edit this file, since this is only for reference on the system
// default settings, and this will overwritten each time "Default Settings..." is clicked.
// If you wish to override these settings, go to // File > Edit Settings... instead.
//
// The settings generated here may change depending on the loaded plugins, which have their own
// default settings.
{}

'''


root_schema = RootSchema()
def validate_schema(schema):
    for field in schema.fields.values():
        # make sure fields have a default replacement for missing fields
        assert field.missing != missing_


_settings = BUILTIN_SETTINGS
_theme = None
_settings_err = None  

def load_theme_settings():
    """Reload all settings from the default settings path.
    
    The exceptions are not immediately thrown since the first time the settings are loaded, the 
    app has not been initialized. So we wait until it is, and then display an error dialog if there
    is a previously recorded error.
    """
    global _theme, _settings, _settings_err
    cur_settings = dict()
    if os.path.isfile(GetThemeSettingsPath ()):
        with open(GetThemeSettingsPath (), 'r') as fp:
            try:
                cur_settings = commentjson.load(fp)
            except JSONLibraryException as e:
                _settings_err = e
                if _theme is not None:
                    # theme has already been loaded, so don't modify it. Otherwise load all
                    # defaults.
                    return
    try:
        temp = root_schema.load(cur_settings)
        config = temp
    except ValidationError as e:
        _settings_err = e
        if _theme is not None:
            return
        config = root_schema.load({})
    _theme = copy.copy(config['theme'])
    _settings = copy.copy(BUILTIN_SETTINGS)


def pop_settings_err():
    """If there was error when loading the settings JSON, this would be not None. Used by canvas to
    display a warning message after the window is created.

    The error is cleared when this is called.
    """
    global _settings_err
    ret = _settings_err
    _settings_err = None
    return ret


def get_default_raw_settings():
    return root_schema.dump(root_schema.load({}))


def get_setting(setting_attr) -> Any:
    return _settings[setting_attr]


def get_theme(theme_attr) -> Any:
    global _theme
    return _theme[theme_attr]


def add_plugin_schema(name: str, schema: Schema):
    # TODO 
    pass
