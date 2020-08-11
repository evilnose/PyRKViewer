"""Custom events dispatched by the canvas.

These events may later be used within a plugin system, where plugins are allowed to bind their own
handlers to these events.
"""

# pylint: disable=maybe-no-member
import wx
from wx.lib.newevent import NewEvent


#WillSelectNodesEvent, EVT_WILL_SELECT_NODES = NewEvent()
"""Called before the list of selected nodes changes.

Note:
    Not implemented.
"""

DidSelectNodesEvent, EVT_DID_SELECT_NODES = NewEvent()
"""Called after the list of selected nodes has changed

Attributes:

"""

