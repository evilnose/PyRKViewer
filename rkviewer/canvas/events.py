"""Custom events dispatched by the canvas.

These events may later be used within a plugin system, where plugins are allowed to bind their own
handlers to these events.
"""

# pylint: disable=maybe-no-member
import wx
from wx.lib.newevent import NewEvent


def get_canvas():
    """
    A hacky way to get the canvas object. Must be called after the app has started running.
    """
    windows = wx.GetTopLevelWindows()
    for window in windows:
        if hasattr(window, 'main_panel'):
            return window.main_panel.canvas
    assert False, "Could not find the main window (of type MyFrame)!"


#WillSelectNodesEvent, EVT_WILL_SELECT_NODES = NewEvent()
"""Called before the list of selected nodes changes.

Note:
    Not implemented.
"""

SelectionDidUpdateEvent, EVT_SELECTION_DID_UPDATE = NewEvent()
"""Called after the list of selected nodes and/or reactions has changed.

Attributes:
    node_idx (Set[int]): The indices of the list of selected nodes.
    reaction_idx (Set[int]): The indices of the list of selected reactions.
"""

CMoveNodeEvent, EVT_C_MOVE_NODE = NewEvent()  # TODO document
"""Called after the controller is notified of a node being moved.

One should use this to request controller to save unsaved changes elsewhere, e.g. if any
associated reactions were changed and need to be saved.
"""

NodeDidMoveEvent, EVT_NODE_DID_MOVE = NewEvent()
"""Called after the position of a node changes in any situation.

TODO implement this manually for move by form and move by dragging. Also provide a list of
indices. After that, update elements.py so that if all nodes in a reaction are moved at once,
move the centroid handle of the bezier as well.

If multiple nodes are moved at once (e.g. by dragging), then this event is issued multiple times,
once for each node.

Attributes:
    node (Node): The node that was moved.
    old_pos (Vec2): The position of the node before it was moved.
"""

DidDragMoveNodesEvent, EVT_DID_DRAG_MOVE_NODES = NewEvent()
"""Called after the list of selected nodes has been moved by dragging.

Attributes:
    node_ids (List[str]): The list of IDs of the resized nodes.
    new_positions (List[Vec2]): The list of new positions of the resized nodes.

Note:
    This event triggers only if the user has performed a drag operation, and not, for example,
    if the user moved a node in the edit panel.
"""

DidDragResizeNodesEvent, EVT_DID_DRAG_RESIZE_NODES = NewEvent()
"""Called after the list of selected nodes has been resized by dragging.

Attributes:
    node_ids (List[str]): The list of IDs of the resized nodes.
    new_sizes (List[Vec2]): The list of new sizes of the resized nodes.

Note:
    This event triggers only if the user has performed a drag operation, and not, for example,
    if the user resized a node in the edit panel.
"""

DidUpdateCanvasEvent, EVT_DID_UPDATE_CANVAS = NewEvent()
"""Called after the canvas has been updated by the controller.

Attributes:
    nodes (list[Node]): The list of nodes.
    reaction (list[Reaction]): The list of reactions.
"""
