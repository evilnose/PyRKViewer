"""Utility functions"""
# pylint: disable=maybe-no-member
import wx
from itertools import tee
import os
import sys
from typing import Any, Callable, Collection, Iterable, List, Set, Tuple, TypeVar
from .canvas.state import cstate
from .canvas.geometry import Node


def convert_position(fn):
    """Decorator that converts the event position to one that is relative to the receiver."""

    def ret(self, evt):
        client_pos = evt.GetPosition()  # get raw position
        screen_pos = evt.EventObject.ClientToScreen(client_pos)  # convert to screen position
        relative_pos = self.ScreenToClient(screen_pos)  # convert to receiver position
        # call function
        copy = evt.Clone()
        copy.SetPosition(relative_pos)
        copy.foreign = not (self is evt.EventObject)
        fn(self, copy)
        evt.Skip()

    return ret


def get_nodes_by_idx(nodes: List[Node], indices: Collection[int]):
    """Simple helper that maps the given list of indices to their corresponding nodes."""
    ret = [n for n in nodes if n.index in indices]
    assert len(ret) == len(indices)
    return ret


def get_nodes_by_ident(nodes: List[Node], ids: Collection[str]):
    ret = [n for n in nodes if n.id_ in ids]
    assert len(ret) == len(ids)
    return ret


def no_rzeros(num: float, precision: int) -> str:
    assert precision > 0
    fmt = '{:.' + str(precision) + 'f}'
    return fmt.format(num).rstrip('0').rstrip('.')


def on_msw() -> bool:
    """Returns whether we are running on Windows."""
    return os.name == 'nt'


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = getattr(sys, '_MEIPASS')
    else:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, 'resources', relative_path)


def pairwise(iterable: Iterable) -> Iterable:
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def rgba_to_wx_colour(rgb: int, alpha: float) -> wx.Colour:
    """Given RGBA color, return wx.Colour.

    Args:
        rgb: RGB color in hex format.
        alpha: The opacity of the color, ranging from 0.0 to 1.0.
    """
    b = rgb & 0xff
    g = (rgb >> 8) & 0xff
    r = (rgb >> 16) & 0xff
    return wx.Colour(r, g, b, int(alpha * 255))

