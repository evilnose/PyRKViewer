"""Custom events dispatched by the canvas.

These events may later be used within a plugin system, where plugins are allowed to bind their own
handlers to these events.
"""

from dataclasses import dataclass
from rkviewer.canvas.geometry import Vec2
from rkviewer.canvas.data import Node, Reaction
from collections import defaultdict
from typing import Callable, DefaultDict, Dict, List, Set, Type, TypeVar


class CanvasEvent:
    pass


@dataclass
class SelectionDidUpdateEvent(CanvasEvent):
    """Called after the list of selected nodes and/or reactions has changed.

    Attributes:
        node_idx (Set[int]): The indices of the list of selected nodes.
        reaction_idx (Set[int]): The indices of the list of selected reactions.
    """
    node_idx: Set[int]
    reaction_idx: Set[int]


@dataclass
class CanvasDidUpdateEvent(CanvasEvent):
    """Called after the canvas has been updated by the controller.

    Attributes:
        nodes (list[Node]): The list of nodes.
        reaction (list[Reaction]): The list of reactions.
    """
    nodes: List[Node]
    reactions: List[Reaction]


@dataclass
class NodesDidMoveEvent(CanvasEvent):
    """Called after the position of a node changes in any situation.

    TODO implement this manually for move by form and move by dragging. Also provide a list of
    indices. After that, update elements.py so that if all nodes in a reaction are moved at once,
    move the centroid handle of the bezier as well.

    If multiple nodes are moved at once (e.g. by dragging), then this event is issued multiple
    times, once for each node.

    Attributes:
        nodes: The nodes that were moved.
        offset: The position offset.
    """
    nodes: List[Node]
    offset: Vec2
    dragged: bool


@dataclass
class DidCommitNodePositionsEvent(CanvasEvent):
    """Called after the position of a node changes in any situation.

    TODO implement this manually for move by form and move by dragging. Also provide a list of
    indices. After that, update elements.py so that if all nodes in a reaction are moved at once,
    move the centroid handle of the bezier as well.

    If multiple nodes are moved at once (e.g. by dragging), then this event is issued multiple
    times, once for each node.

    Attributes:
        nodes: The nodes that were moved.
        offset: The position offset.
    """


@dataclass
class DidDragResizeNodesEvent(CanvasEvent):
    """Called after the list of selected nodes has been moved by dragging.

    Attributes:
        nodes (List[Node]): The list of resized nodes.
        ratio: (Vec2): The resize ratio.

    Note:
        This event triggers only if the user has performed a drag operation, and not, for example,
        if the user moved a node in the edit panel.
    """
    nodes: List[Node]
    ratio: Vec2


EventCallback = Callable[[CanvasEvent], None]
event_map: DefaultDict[Type[CanvasEvent], List[EventCallback]] = defaultdict(list)


def bind_handler(cls: Type[CanvasEvent], callback: EventCallback):
    event_map[cls].append(callback)


def post_event(evt: CanvasEvent):
    for callback in event_map[type(evt)]:
        callback(evt)
