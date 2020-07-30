# pylint: disable=maybe-no-member
import wx
from .types import Rect, Vec2


def IodToWxColour(rgb: int, alpha: float):
    b = rgb & 0xff
    g = (rgb >> 8) & 0xff
    r = (rgb >> 16) & 0xff
    return wx.Colour(r, g, b, int(alpha * 255))


def WithinRect(pos: Vec2, rect: Rect) -> bool:
    end = rect.position + rect.size
    return pos.x >= rect.position.x and pos.y >= rect.position.y and pos.x <= end.x and \
        pos.y <= end.y
