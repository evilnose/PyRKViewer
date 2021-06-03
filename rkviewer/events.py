"""Custom events dispatched by the canvas.

These events may later be used within a plugin system, where plugins are allowed to bind their own
handlers to these events.
"""
# from __future__ import annotations
# pylint: disable=maybe-no-member
from collections import defaultdict
from dataclasses import dataclass, fields, is_dataclass
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type, Union,
)

import wx

from rkviewer.canvas.geometry import Vec2


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
        compartment_indices: The indices of the list of selected compartments.
    """
    node_indices: Set[int]
    reaction_indices: Set[int]
    compartment_indices: Set[int]


@dataclass
class CanvasDidUpdateEvent(CanvasEvent):
    """Called after the canvas has been updated by the controller."""
    pass


@dataclass
class DidMoveNodesEvent(CanvasEvent):
    """Called after the position of a node changes but has not been committed to the model.

    This event may be called many times, continuously as the user drags a group of nodes. Note that
    only after the drag operation has ended, is model notified of the move for undo purposes. See
    DidCommitDragEvent.

    Attributes:
        node_indices: The indices of the nodes that were moved.
        offset: The position offset. If all nodes were moved by the same offset, then a single Vec2
                is given; otherwise, a list of offsets are given, with each offset matching a node.
        dragged: Whether the resize operation was done by the user dragging, and not, for exmaple,
                 through the form.
        by_user: Whether the event was performed by the user or through a plugin.
    """
    node_indices: List[int]
    offset: Union[Vec2, List[Vec2]]
    dragged: bool
    by_user: bool = True


@dataclass
class DidMoveCompartmentsEvent(CanvasEvent):
    """
    Same as `DidMoveNodesEvent` but for compartments.

    Attributes:
        compartment_indices: The indices of the compartments that were moved.
        offset: The position offset. If all compartments were moved by the same offset,
                then a single Vec2 is given; otherwise, a list of offsets are given,
                with each offset matching a node.
        dragged: Whether the resize operation was done by the user dragging, and not, for exmaple,
                 through the form.
        by_user: Whether the event was performed by the user or through a plugin.
    """
    compartment_indices: List[int]
    offset: Union[Vec2, List[Vec2]]
    dragged: bool
    by_user: bool = True


@dataclass
class DidResizeNodesEvent(CanvasEvent):
    """Called after the list of selected nodes has been resized.

    Attributes:
        node_indices: The indices of the list of resized nodes.
        ratio: The resize ratio.
        dragged: Whether the resize operation was done by the user dragging, and not, for exmaple,
                 through the form.
        by_user: Whether the event was performed by the user or through a plugin.
    """
    node_indices: List[int]
    ratio: Vec2
    dragged: bool
    by_user: bool = True


@dataclass
class DidResizeCompartmentsEvent(CanvasEvent):
    """TODO document (same as DidResizeNodesEvent)
    """
    compartment_indices: List[int]
    ratio: Union[Vec2, List[Vec2]]
    dragged: bool
    by_user: bool = True


@dataclass
class DidCommitDragEvent(CanvasEvent):
    """Dispatched after any continuously emitted dragging event has concluded.

    This is dispatched for any event that is posted in quick intervals while the mouse left
    button is held while moving, i.e. "dragging" events. This includes: DidMoveNodesEvent,
    DidMoveCompartmentsEvent, DidResizeNodesEvent, DidResizeCompartmentsEvent,
    and DidResizeMoveBezierHandlesEvent. This event is emitted after the left mouse button is
    released, the model is notified of the change, and the action is complete.
    """
    source: Any


@dataclass
class DidMoveBezierHandleEvent(CanvasEvent):
    """Dispatched after a Bezier handle is moved.

    Attributes:
        net_index: The network index.
        reaction_index: The reaction index.
        node_index: The index of the node whose Bezier handle moved. -1 if the source centroid
                    handle was moved, or -2 if the dest centroid handle was moved.
        direct: Automatically true when by_user is False. Otherwise, True if the handle is
                moved by the user dragging the handle directly, and False if the handle was moved
                by the user dragging the node associated with that handle.
        by_user: Whether the event was performed by the user or through a plugin.
    """
    net_index: int
    reaction_index: int
    node_index: int
    by_user: bool
    direct: bool


@dataclass
class DidMoveReactionCenterEvent(CanvasEvent):
    """Dispatched after the reaction center is moved by the user.

    Note that this is not triggered if the center moved automatically due to nodes moving.

    Attributes:
        net_index: The network index.
        reaction_index: The reaction index.
        offset: The amount moved.
        dragged: Whether the center is moved by the user dragging (it could have been through the
                 form).
    """
    net_index: int
    reaction_index: int
    offset: Vec2
    dragged: bool


@dataclass
class DidAddNodeEvent(CanvasEvent):
    """Called after a node has been added.

    Attributes:
        node: The index of the node that was added.

    Note:
        This event triggers only if the user has performed a drag operation, and not, for example,
        if the user moved a node in the edit panel.
    TODO in the documentation that this event and related ones (and DidDelete-) are emitted before
    controller.end_group() is called. As an alternative, maybe create a call_after() function
    similar to wxPython? it should be called in OnIdle() or Refresh()
    """
    node: int


@dataclass
class DidDeleteEvent(CanvasEvent):
    """Called after a node has been deleted.

    Attributes:
        node_indices: The set of nodes (indices )that were deleted.
        reaction_indices: The set of reactions (indices) that were deleted.
        compartment_indices: The set of compartment (indices) that were deleted.
    """
    node_indices: Set[int]
    reaction_indices: Set[int]
    compartment_indices: Set[int]


@dataclass
class DidAddReactionEvent(CanvasEvent):
    """Called after a reaction has been added.

    Attributes:
        reaction: The Reaction that was added.
    """
    index: int


@dataclass
class DidAddCompartmentEvent(CanvasEvent):
    """Called after a compartment has been added.

    Attributes:
        compartment: The Compartment that was added.
    """
    index: int


@dataclass
class DidChangeCompartmentOfNodesEvent(CanvasEvent):
    """Called after one or more nodes have been moved to a new compartment.

    Attributes:
        node_indices: The list of node indices that changed compartment.
        old_compi: The old compartment index, -1 for base compartment.
        new_compi: The new compartment index, -1 for base compartment.
        by_user: Whether this event was triggered directly by a user action, as opposed to by a
                 plugin.
    """
    node_indices: List[int]
    old_compi: int
    new_compi: int
    by_user: bool = True


@dataclass
class DidModifyNodesEvent(CanvasEvent):
    """Called after a property of one or more nodes has been modified, excluding position or size.

    For position and size events, see DidMove...Event() and DidResize...Event()

    Attributes:
        nodes: The indices of the list of nodes that were modified.
        by_user: Whether this event was triggered directly by a user action and not, for example,
                 by a plugin.
    """
    indices: List[int]
    by_user: bool = True


@dataclass
class DidModifyReactionEvent(CanvasEvent):
    """Called after a property of one or more nodes has been modified, excluding position.

    Attributes:
        indices: The indices of the list of reactions that were modified.
        by_user: Whether this event was triggered directly by a user action and not, for example,
                 by a plugin.
    """
    indices: List[int]
    by_user: bool = True


@dataclass
class DidModifyCompartmentsEvent(CanvasEvent):
    """Called after a property of one or more compartments has been modified, excluding position or size.

    For position and size events, see DidMove...Event() and DidResize...Event()

    Attributes:
        indices: The indices of list of compartments that were modified.
    """
    indices: List[int]


@dataclass
class DidUndoEvent(CanvasEvent):
    """Called after an undo action is done."""
    by_user: bool = True


@dataclass
class DidRedoEvent(CanvasEvent):
    """Called after a redo action is done."""
    by_user: bool = True


@dataclass
class DidPaintCanvasEvent(CanvasEvent):
    """Called after the canvas has been painted.

    Attributes:
        gc: The graphics context of the canvas.
    """
    gc: wx.GraphicsContext


EventCallback = Callable[[CanvasEvent], None]
class HandlerNode:
    next_: Optional['HandlerNode']
    prev: Optional['HandlerNode']
    handler: EventCallback

    def __init__(self, handler: EventCallback):
        self.handler = handler
        self.next_ = None


# Maps CanvasElement to a dict that maps events to handler nodes
handler_map: Dict[int, Tuple['HandlerChain', HandlerNode]] = dict()
# Maps event to a chain of handlers
event_chains: DefaultDict[Type[CanvasEvent], 'HandlerChain'] = defaultdict(lambda: HandlerChain())

handler_id = 0


class HandlerChain:
    head: Optional[HandlerNode]
    tail: Optional[HandlerNode]

    def __init__(self):
        self.head = None
        self.tail = None
        self.it_cur = None

    def remove(self, node: HandlerNode):
        if node.prev is not None:
            node.prev.next_ = node.next_
        else:
            self.head = node.next_

        if node.next_ is not None:
            node.next_.prev = node.prev
        else:
            self.tail = node.prev

    def __iter__(self):
        self.it_cur = self.head
        return self

    def __next__(self):
        if self.it_cur is None:
            raise StopIteration()

        ret = self.it_cur.handler
        self.it_cur = self.it_cur.next_
        return ret

    def append(self, handler: EventCallback) -> HandlerNode:
        node = HandlerNode(handler)
        if self.head is None:
            assert self.tail is None
            self.head = self.tail = node
        else:
            assert self.tail is not None
            node.prev = self.tail
            self.tail.next_ = node
            self.tail = node

        return node


def bind_handler(evt_cls: Type[CanvasEvent], callback: EventCallback) -> int:
    global handler_id
    ret = handler_id
    chain = event_chains[evt_cls]
    hnode = chain.append(callback)
    handler_map[ret] = (chain, hnode)
    handler_id += 1
    return ret


def unbind_handler(handler_id: int):
    chain, hnode = handler_map[handler_id]
    chain.remove(hnode)
    del handler_map[handler_id]


def post_event(evt: CanvasEvent):
    for callback in iter(event_chains[type(evt)]):
        callback(evt)
