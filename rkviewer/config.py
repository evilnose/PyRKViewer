"""Configuration parameters.
"""
# pylint: disable=maybe-no-member
from typing import Any, Dict, Mapping

from commentjson.commentjson import JSONLibraryException
from rkviewer.utils import get_local_path
from scipy.special.orthogonal import roots_hermite
import wx
import os
from marshmallow import Schema, fields, validate, missing as missing_, ValidationError
from rkviewer.canvas.geometry import Vec2
import copy
import commentjson


# TODO rename get_local_path
config_dir = get_local_path('.rkviewer')
settings_path = os.path.join(config_dir, 'settings.json')
default_settings_path = os.path.join(config_dir, '.default-settings.json')


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


class ThemeSchema(Schema):
    """Schema for the overall theme, i.e. appearance, of the application.

    Attributes:
        overall_bg: The overall background of the application.

    TODO more documentation under attributes and link to this document in Help or settings.json
    """
    # overall background of the application 
    overall_bg = Color(missing=wx.Colour(255, 112, 0))
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
    toolbar_height = Pixel(missing=40)
    edit_panel_width = Pixel(missing=260)
    node_fill = Color(missing=wx.Colour(150, 255, 150, 200))
    node_border = Color(missing=wx.Colour(19, 173, 2))
    node_width = Pixel(missing=50)
    node_height = Pixel(missing=30)
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
    highlighted_handle_color = Color(missing=wx.Colour(255, 112, 0))
    # Padding of the select box, relative to the mininum possible bbox
    select_box_padding = Pixel(missing=5)
    # Length of the squares one uses to drag resize nodes
    select_handle_length = Pixel(missing=8)
    zoom_slider_bg = Color(missing=wx.Colour(150, 150, 150))
    drag_fill = Color(missing=wx.Colour(0, 140, 255, 20))
    drag_border = Color(missing=wx.Colour(0, 140, 255))
    drag_border_width = Pixel(missing=1)
    react_node_padding = Pixel(missing=5)
    react_node_border_width = Pixel(missing=3)
    reactant_border = Color(missing=wx.Colour(255, 100, 100))
    product_border = Color(missing=wx.Colour(0, 214, 125))
    reaction_center_size = Pixel(missing=10)
    reaction_fill = Color(missing=wx.Colour(0, 0, 0))
    reaction_line_thickness = Pixel(missing=2)
    selected_reaction_fill = Color(missing=wx.Colour(0, 140, 255))
    comp_fill = Color(missing=wx.Colour(158, 169, 255, 200))
    comp_border = Color(missing=wx.Colour(0, 29, 255))
    comp_border_width = Pixel(missing=2)
    reaction_radius = Pixel(missing=6)


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


def load_settings():
    """Reload all settings from the default settings path.
    
    The exceptions are not immediately thrown since the first time the settings are loaded, the 
    app has not been initialized. So we wait until it is, and then display an error dialog if there
    is a previously recorded error.
    """
    global _theme, _settings, _settings_err
    cur_settings = dict()
    if os.path.isfile(settings_path):
        with open(settings_path, 'r') as fp:
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
# dumped_config = root_schema.dump(default_config)
