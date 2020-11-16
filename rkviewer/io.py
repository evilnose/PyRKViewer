"""Module that deals with file I/O and serialization/deserialization."""
from rkviewer.iodine import TColor
from marshmallow import Schema, fields, validate, missing as missing_, ValidationError
from .config import get_setting


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

    def _serialize(self, value: TColor, attr, obj, **kwargs):
        ret = [value.r, value.g, value.b]
        if value.a != 255:
            ret += [value.a]
        return ret

    def _deserialize(self, value, attr, data, **kwargs):
        self.list_field.validate(value)
        for val in value:
            Color.range_validate(val)
        return TColor(*value)


class Pixel(fields.Int):
    """Field that represents some length in pixels.

    The only current restriction is that this must be a nonnegative integer, or
    >>> { "some_width": 23 }
    """
    def __init__(self, **kwargs):
        super().__init__(validate=validate.Range(min=0), **kwargs)


class Dim(fields.Float):
    def __init__(self, **kwargs):
        # TODO should we allow 0? Also decide for pixel
        super().__init__(validate=validate.Range(min=0), **kwargs)


class FontSchema(Schema):
    # TODO use this after implemented
    pointSize = Pixel()
    family = str  # TODO change to enum
    style: str
    weight: str
    name: str
    color: TColor


class NodeSchema(Schema):
    id = fields.Str()  # TODO assert unique
    x = Dim()  # TODO validate not out of range of canvas?
    y = Dim()
    w = fields.Float(validate=validate.Range(min=get_setting('min_node_width')))
    h = fields.Float(validate=validate.Range(min=get_setting('min_node_height')))
    compi = fields.Int()
    fillColor = Color()
    outlineColor = Color()
    outlineThickness = Dim()
    # font: TFont

    # TODO add hooks to convert object to TNode
