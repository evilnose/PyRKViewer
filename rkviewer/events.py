"""Custom events dispatched by the canvas.

These events may later be used within a plugin system, where plugins are allowed to bind their own
handlers to these events.
"""
# pylint: disable=maybe-no-member
import wx
from dataclasses import dataclass, is_dataclass, fields
from rkviewer.canvas.geometry import Vec2
from rkviewer.canvas.data import Node, Reaction
from collections import defaultdict
from typing import Callable, DefaultDict, Dict, List, Set, Type, TypeVar


class CanvasEvent:
    def to_tuple(self):
        assert is_dataclass(self), "as_tuple requires the CanvasEvent instance to be a dataclass!"

        return tuple(getattr(self, f.name) for f in fields(self))


@dataclass
class SelectionDidUpdateEvent(CanvasEvent):
    """Called after the list of selected nodes and/or reactions has changed.

    Attributes:
        node_indices: The indices of the list of selected nodes.
        reaction_indices: The indices of the list of selected reactions.
    """
    node_indices: Set[int]
    reaction_indices: Set[int]


@dataclass
class CanvasDidUpdateEvent(CanvasEvent):
    """Called after the canvas has been updated by the controller.

    Attributes:
        nodes: The list of nodes.
        reaction: The list of reactions.
    """
    nodes: List[Node]
    reactions: List[Reaction]


@dataclass
class DidMoveNodesEvent(CanvasEvent):
    """Called after the position of a node changes but has not been committed to the model.

    This event may be called many times, continuously as the user drags a group of nodes. Note that
    only after the drag operation has ended, is model notified of the move for undo purposes. See
    DidCommitNodePositionsEvent.

    Attributes:
        nodes: The nodes that were moved.
        offset: The position offset.
    """
    nodes: List[Node]
    offset: Vec2
    dragged: bool


@dataclass
class DidCommitNodePositionsEvent(CanvasEvent):
    """Called after the node positions are commited to the controller.

    This even is emitted only after a node move action has been regsitered with the controller.
    E.g., when a user drag-moves a ndoe, only after they release the left mouse button is the action
    recorded in the undo stack.
    """


@dataclass
class DidDragResizeNodesEvent(CanvasEvent):
    """Called after the list of selected nodes has been moved by dragging.

    Attributes:
        nodes: The list of resized nodes.
        ratio: The resize ratio.

    Note:
        This event triggers only if the user has performed a drag operation, and not, for example,
        if the user moved a node in the edit panel.
    """
    nodes: List[Node]
    ratio: Vec2


@dataclass
class DidAddNodeEvent(CanvasEvent):
    """Called after a node has been added.

    Attributes:
        node: The node that was added.

    Note:
        This event triggers only if the user has performed a drag operation, and not, for example,
        if the user moved a node in the edit panel.
    """
    node: Node


@dataclass
class DidPaintCanvasEvent(CanvasEvent):
    """Called after the canvas has been painted.

    Attributes:
        gc: The graphics context of the canvas.
    """
    gc: wx.GraphicsContext


EventCallback = Callable[[CanvasEvent], None]
event_map: DefaultDict[Type[CanvasEvent], List[EventCallback]] = defaultdict(list)


def bind_handler(cls: Type[CanvasEvent], callback: EventCallback):
    event_map[cls].append(callback)


def post_event(evt: CanvasEvent):
    for callback in event_map[type(evt)]:
        callback(evt)
