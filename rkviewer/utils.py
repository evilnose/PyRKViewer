# pylint: disable=maybe-no-member
import wx


def IodToWxColour(rgb: int, alpha: float):
    b = rgb & 0xff
    g = (rgb >> 8) & 0xff
    r = (rgb >> 16) & 0xff
    return wx.Colour(r, g, b, int(alpha * 255))
