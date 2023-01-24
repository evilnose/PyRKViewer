"""Utility functions"""
# pylint: disable=maybe-no-member
import wx
from itertools import tee
import os
import platform
import subprocess
import sys
from typing import Any, Callable, Dict, Iterable, List, Tuple, Type, TypeVar
from dataclasses import is_dataclass
from pathlib import Path


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


def get_local_path(relative_path):
    """Get path relative to the executable, or the working dir if not bundled."""
    return os.path.abspath(relative_path)


# def get_bundled_path(relative_path):
#     """Given a path relative to the application bundle, return the absolute path.
    
#     Specifically for files bundled with the application, e.g. resources.
#     """
#     if hasattr(sys, '_MEIPASS'):
#         # PyInstaller creates a temp folder and stores path in _MEIPASS
#         base_path = getattr(sys, '_MEIPASS')
#     else:
#         base_path = os.path.abspath(".")

#     return os.path.join(base_path, relative_path)


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""

    source_path = Path(__file__).resolve()
    source_dir = source_path.parent
    return source_dir.joinpath('resources').joinpath(relative_path).as_posix()


def start_file(abs_path: str):
    # Tell OS to open the file for editing. From https://stackoverflow.com/a/435669/9171534
    if platform.system() == 'Darwin':       # macOS
        subprocess.call(('open', abs_path))
    elif platform.system() == 'Windows':    # Windows
        os.startfile(abs_path)
    else:                                   # linux variants
        subprocess.call(('xdg-open', abs.path))


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


def opacity_mul(color: wx.Colour, fraction: float) -> wx.Colour:
    return wx.Colour(color.Red(), color.Green(), color.Blue(), int(color.Alpha() * fraction))


def change_opacity(color: wx.Colour, new_op: int):
    return wx.Colour(color.Red(), color.Green(), color.Blue(), new_op)


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


T = TypeVar('T')
def gchain(*iterables: Iterable[T]) -> Iterable[Tuple[int, T]]:
    # chain('ABC', 'DEF') --> (0,A) (0,B) (0,C) (1,D) (1,E) (1,F)
    i = 0
    for it in iterables:
        for element in it:
            yield (i, element)
        i += 1


# Force dataclass to use kwargs, from https://gist.github.com/mikeholler/4be180627d3f8fceb55704b729464adb#file-dataclass_utils-py
_T = TypeVar("_T")
_Self = TypeVar("_Self")
_VarArgs = List[Any]
_KWArgs = Dict[str, Any]


def _kwarg_only_init_wrapper(
        self: _Self,
        init: Callable[..., None],
        *args: _VarArgs,
        **kwargs: _KWArgs
) -> None:
    if len(args) > 0:
        raise TypeError(
            f"{type(self).__name__}.__init__(self, ...) only allows keyword arguments. Found the "
            f"following positional arguments: {args}"
        )
    init(self, **kwargs)


def require_kwargs_on_init(cls: Type[_T]) -> Type[_T]:
    """
    Force a dataclass's init function to only work if called with keyword arguments.
    If parameters are not positional-only, a TypeError is thrown with a helpful message.
    This function may only be used on dataclasses.
    This works by wrapping the __init__ function and dynamically replacing it. Therefore,
    stacktraces for calls to the new __init__ might look a bit strange. Fear not though,
    all is well.
    Note: although this may be used as a decorator, this is not advised as IDEs will no longer
    suggest parameters in the constructor. Instead, this is the recommended usage::
        from dataclasses import dataclass
        @dataclass
        class Foo:
            bar: str
        require_kwargs_on_init(Foo)
    """
    if cls is None:
        raise TypeError("Cannot call with cls=None")
    if not is_dataclass(cls):
        raise TypeError(
            f"This decorator only works on dataclasses. {cls.__name__} is not a dataclass."
        )

    original_init = cls.__init__

    def new_init(self: _Self, *args: _VarArgs, **kwargs: _KWArgs) -> None:
        _kwarg_only_init_wrapper(self, original_init, *args, **kwargs)

    # noinspection PyTypeHints
    cls.__init__ = new_init  # type: ignore

    return cls
