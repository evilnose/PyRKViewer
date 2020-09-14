"""Utility functions"""
# pylint: disable=maybe-no-member
import wx
from itertools import tee
import os
import sys
from typing import Any, Callable, Iterable


def convert_position(fn):
    """Decorator that converts the event position to one that is relative to the receiver."""

    def ret(self, evt):
        if self is not evt.EventObject:
            client_pos = evt.GetPosition()  # get raw position
            screen_pos = evt.EventObject.ClientToScreen(client_pos)  # convert to screen position
            relative_pos = self.ScreenToClient(screen_pos)  # convert to receiver position
            # call function
            copy = evt.Clone()
            copy.SetPosition(relative_pos)
            copy.foreign = True
            fn(self, copy)
            evt.Skip()
        else:
            copy = evt
            copy.foreign = False
            fn(self, copy)

    return ret


def no_rzeros(num: float, precision: int) -> str:
    """Returns string of the num with the given precision, but with trailing zeros removed."""
    assert precision > 0
    fmt = '{:.' + str(precision) + 'f}'
    return fmt.format(num).rstrip('0').rstrip('.')


def on_msw() -> bool:
    """Returns whether we are running on Windows."""
    return os.name == 'nt'


def get_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = getattr(sys, '_MEIPASS')
    else:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def resource_path(relative_path):
    return get_path(os.path.join('resources', relative_path))


def pairwise(iterable: Iterable) -> Iterable:
    """s -> (s0,s1), (s1,s2), (s2, s3), ..."""
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


class ButtonGroup:
    """Class for keeping track of a group of buttons, where exactly one of them can be selected.

    Attributes:
        Callback: The callback function type called with ID of the selected button as argument.
    """
    Callback = Callable[[str], None]

    def __init__(self, callback: Callback):
        """Construct a ButtonGroup.

        Args:
            callback: The callback function called when a new button is selected.
        """
        self.callback = callback
        self.buttons = []
        self.selected = None  # should be tuple (button, group_id)

    def AddButton(self, button: wx.ToggleButton, identifier: Any):
        """Add a button with the given identifier.
        
        When this button is clicked, callback is called with the identifier.
        """
        # right now there is no type info for wxPython, so this is necessary
        assert isinstance(button, wx.ToggleButton)

        self.buttons.append(button)
        button.Bind(wx.EVT_TOGGLEBUTTON, self._MakeToggleFn(button, identifier))

        # First added button; make it selected
        if self.selected is None:
            self.selected = (button, identifier)
            button.SetValue(True)
            self.callback(identifier)

    def _MakeToggleFn(self, button: wx.ToggleButton, group_id: Any):
        """Create the function to be called by a specific button in the group when it is clicked.
        """
        # right now there is no type info for wxPython, so this is necessary
        assert isinstance(button, wx.ToggleButton)

        def ret(evt):
            assert self.selected is not None, "There must be at least one button in ButtonGroup!"

            if evt.IsChecked():
                button.SetValue(True)
                selected_btn, selected_id = self.selected
                if selected_id != group_id:
                    selected_btn.SetValue(False)
                    self.selected = (button, group_id)
                    self.callback(group_id)
            else:
                # don't allow de-select
                button.SetValue(True)
        return ret

def int_round(n: float) -> int:
    return int(round(round(n, 2)))

def even_round(n: float) -> int:
    """Round to the nearest even integer"""
    return int(round(n / 2)) * 2
