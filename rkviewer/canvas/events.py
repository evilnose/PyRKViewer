"""Custom events dispatched by the canvas.

These events may later be used within a plugin system, where plugins are allowed to bind their own
handlers to these events.
"""

# pylint: disable=maybe-no-member
from wx.lib.newevent import NewEvent


#WillSelectNodesEvent, EVT_WILL_SELECT_NODES = NewEvent()
"""Called before the list of selected nodes changes.

Note:
    Not implemented.
"""

DidUpdateSelectionEvent, EVT_DID_UPDATE_SELECTION = NewEvent()
"""Called after the list of selected nodes and/or reactions has changed.

Attributes:
    node_idx (Set[int]): The indices of the list of selected nodes.
    reaction_idx (Set[int]): The indices of the list of selected reactions.
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
