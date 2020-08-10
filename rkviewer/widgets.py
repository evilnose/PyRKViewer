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


# TODO this is obsolete. Delete this
class DragDrop(wx.Panel):
    Callback = Callable[[wx.Window, wx.Point], None]

    window: wx.Window
    drop_callback: Callback
    _position: wx.Point
    _dragging: bool

    def __init__(self, *args, window: wx.Window, drop_callback: Callback, **kw):
        """Constructs a DragDrop instance.

        The window parameter should be the widget over which the dragging would occur,
        i.e. the operating area of the DragDrop widget.
        """
        super().__init__(*args, **kw)
        self.RegisterAllChildren(window)

        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)

        self.window = window
        self.drop_callback = drop_callback
        self._dragging = False

    def RegisterAllChildren(self, widget):
        """Connect all descendants of this widget to relevant events.

        wxPython does not propagate events like LEFT_UP and MOTION up to the
        parent of the window that received it. Therefore normally there is 
        no way for DragDrop to detect a mouse event if it occurred on top
        of a child widget of window. This function solves this problem by
        recursively connecting all child widgets of window to trigger the DragDrop
        handlers. Note that whatever event registered here must do evt.Skip() so
        that the child itself can handle its event as well.

        This solution is from https://stackoverflow.com/a/27911300/9171534
        """
        if self != widget:
            widget.Connect(wx.ID_ANY, -1, wx.wxEVT_LEFT_UP, self.OnLeftUp)
            widget.Connect(wx.ID_ANY, -1, wx.wxEVT_MOTION, self.OnMotion)

        for child in widget.GetChildren():
            self.RegisterAllChildren(child)

    def OnLeftDown(self, evt):
        self._dragging = True

    def OnLeftUp(self, evt):
        if self._dragging:
            self._dragging = False
            self.drop_callback(evt.GetEventObject(), evt.GetPosition())
        evt.Skip()

    def OnMotion(self, evt):
        obj = evt.GetEventObject()
        assert obj is not None

        # convert to position relative to self.window
        client_pos = evt.GetPosition()
        screen_pos = obj.ClientToScreen(client_pos)
        self._position = self.window.ScreenToClient(screen_pos)

        if self._dragging:
            self.window.Refresh()
        evt.Skip()

    @property
    def position(self):
        return self._position

    @property
    def dragging(self):
        return self._dragging
