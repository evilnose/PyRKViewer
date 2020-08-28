# pylint: disable=maybe-no-member
import wx
from typing import Callable, Any


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
    