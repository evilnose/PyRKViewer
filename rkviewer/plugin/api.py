"""
API for the RKViewer GUI and model. Allows viewing and modifying the network model.
"""

# pylint: disable=maybe-no-member
#from rkviewer.mvc import NetIndexError
# from __future__ import annotations
from dataclasses import field, dataclass
from traitlets.traitlets import default

from wx.core import EVT_LIST_END_LABEL_EDIT
from rkviewer.iodine import DEFAULT_SHAPE_FACTORY
from rkviewer.canvas.canvas import Canvas
from rkviewer.events import DidChangeCompartmentOfNodesEvent, post_event
from rkviewer.canvas.utils import default_handle_positions as _default_handle_positions
from rkviewer.utils import gchain, require_kwargs_on_init
from rkviewer.canvas.geometry import Rect, pt_in_rect
from rkviewer.config import DEFAULT_ARROW_TIP
import wx
import copy
from contextlib import contextmanager
from rkviewer.mvc import IController, ModifierTipStyle
from typing import Any, KeysView, List, Optional, Set, Tuple, Union
from rkviewer.canvas import data
from rkviewer.canvas.state import cstate, ArrowTip
from rkviewer.config import Color, get_setting, get_theme
# re-export events and data "structs" TODO how will documentation work here?
from rkviewer.canvas.data import CompositeShape, Node, Reaction, Compartment, Vec2
from rkviewer.canvas import data
import logging
from logging import Logger

# TODO allow modification of theme and setting in the GUI

_canvas: Optional[Canvas] = None
_controller: Optional[IController] = None
_plugin_logger = logging.getLogger('plugin')


class CustomNone:
    """Used for default parameters where 'None' is a valid and possible input."""
    pass


def get_canvas() -> Optional[Canvas]:
    '''Obtain the Canvas instance.

    This is for advanced use cases that require direct access to the Canvas, for operations that
    have not been implmented in the API.
    '''
    return _canvas


def get_controller() -> Optional[IController]:
    return _controller



# @require_kwargs_on_init
@dataclass(frozen=True, eq=True)
class NodeData:
    """Class that holds all the necessary data for a Node.

    Attributes:
        index:          Node index. Despite the name, this is the value that acts as the constant
                            identifier for nodes. ID, on the other hand, may be modified. If this is -1, it
                            means that this Node is not currently part of a network.
        id:             Node ID. Note: NOT constant; see `index` for constant identifiers.
        net_index:      The index of the network that this node is in.
        position:       The top-left position of the node bounding box as (x, y).
        size:           The size of the node bounding box as (w, h).
        comp_idx:       The index of the compartment that this node is in, or -1 if it is in the base
                            compartment.
        floating_node:  Set true if you want the node to have floating status or false for boundary
                            status (default is floating)
        lock_node:      Set false if you want the node to move or true for block (default is false)
        original_index: If this is an alias node, this is the index of the original node. Otherwise
                            this is -1.
        shape_index:    The composite shape index of the node. 0 for rectangle, 1 for circle, and
                            so on. For the full list of shapes, view iodine.py
        shape:          The CompositeShape object of the node. This is guaranteed to match the shape
                            as indicated by shape_index. This field is present for convenient access
                            of the shape's properties, including the primitives contained within and
                            the properties of the primitive.
        concentration:  The concentration of the node. Default to zero, must not be negative.
        node_name:      The name of the node.
        node_SBO:       The SBO of the node.
    """
    net_index: int = field()
    id: str = field()
    position: Vec2 = field(default=Vec2())
    size: Vec2 = field(default=Vec2())
    comp_idx: int = field(default=-1)
    index: int = field(default=-1)
    floating_node: bool = field(default=True)
    lock_node: bool = field(default=False)
    original_index: int = field(default=-1)
    shape_index: int = field(default=0)
    shape: CompositeShape = field(default_factory=DEFAULT_SHAPE_FACTORY.produce)
    concentration: float = field(default=0.0)
    node_name: str = field(default='')
    node_SBO: str = field(default='')

    @property
    def bounding_rect(self) -> Rect:
        return Rect(self.position, self.size)


# @require_kwargs_on_init
@dataclass(frozen=True)
class ReactionData:
    """Class that bolds the data of a Reaction, except for stoich information (TODO?).

    Attributes:
        index: reaction index. Despite the name, this is the value that acts as the constant
               identifier for reactions. ID, on the other hand, may be modified.
        id: Reaction ID. Note: NOT constant; see `index` for constant identifiers.
        net_index: The index of the network that this node is in.
        fill_color: reaction fill color.
        line_thickness: Bezier curve thickness.
        rate_law: reaction rate law.
        sources: The source (reactant) node indices.
        targets: The target (product) node indices.
    """
    id: str = field()
    net_index: int = field()
    fill_color: Color = field()
    line_thickness: float = field()
    sources: List[int] = field()
    targets: List[int] = field()
    center_pos: Optional[Vec2] = field(default=None)
    rate_law: str = field(default='')
    using_bezier: bool = field(default=True)
    index: int = field(default=-1)
    modifiers: Set[int] = field(default_factory=set)
    modifier_tip_style: ModifierTipStyle = field(default=ModifierTipStyle.CIRCLE)

    @property
    def centroid(self) -> Vec2:
        """The position of the centroid of this reaction"""
        return compute_centroid(self.net_index, self.sources, self.targets)

    @property
    def real_center(self) -> Vec2:
        """The position of the reaction center circle.

        If the center has been manually moved by the user, then this would be equal to center_pos.
        Otherwise this is equal to the dynamically computed centeroid position.
        """
        return self.center_pos if self.center_pos is not None else self.centroid


# @require_kwargs_on_init
@dataclass(frozen=True)
class CompartmentData:
    """
    Attributes:
        index: Compartment index. Despite the name, this is the value that acts as the constant
               identifier for compartments. ID, on the other hand, may be modified.
        id: Compartment ID. Note: NOT constant; see `index` for constant identifiers.
        net_index: The index of the network that this is in.
        nodes: Indices for nodes that are within this compartment.
        volume: Size (i.e. length/area/volume/...) of the container, for simulation purposes.
        position: Position of the top-left corner of the bounding box, (x, y).
        size: Size of the bounding box, as (w. h).
        fill_color: The fill color of the compartment.
        border_color: The border color of the compartment.
        border_width: The border width of the compartment.
    """
    index: int = field()
    id: str = field()
    net_index: int = field()
    nodes: List[int] = field()
    volume: float = field()
    position: Vec2 = field()
    size: Vec2 = field()
    fill_color: Color = field()
    border_color: Color = field()
    border_width: float = field()


def _to_color(color: wx.Colour) -> Color:
    return Color(color.Red(), color.Green(), color.Blue(), color.Alpha())


def _to_wxcolour(color: Color) -> wx.Colour:
    return wx.Colour(color.r, color.g, color.b, color.a)


def init_api(canvas: Canvas, controller: IController):
    """Initializes the API; for internal use only."""
    global _canvas, _controller
    assert canvas is not None
    assert controller is not None
    _canvas = canvas
    _controller = controller


def uninit_api():
    """Uninitialize the API; for internal use only."""
    global _canvas, _controller
    _canvas = None
    _controller = None


def refresh_canvas():
    '''Tell the canvas to redraw itself.

    This does not need to be called manually when there are changes to the model, since the model
    automatically updates the canvas. But if changes are made only to CanvasElements, then this is
    required to reflect the changes.
    '''
    _canvas.LazyRefresh()


def clear_network(net_index: int):
    """Clear the given network."""
    _controller.clear_network(net_index)


def cur_net_index() -> int:
    """The current network index."""
    return _canvas.net_index


def logger() -> Logger:
    """Return the logger for plugins. Use this for logging inside plugins."""
    return _plugin_logger


def group_action():
    """Context manager for doing a group operation in the _controller, for undo/redo purposes.

    Examples:
        As shown here, calls to the API within the group_action context are considered to be
        within one single group as far as undoing/redoing is concerned.

        >>> with api.group_action():
        >>>     for node in some_node_list:
        >>>         api.update_node(...)
        >>>     api.update_reaction(...)
        >>> api.update_node(...)  # This is now a new action.

    """
    return _controller.group_action()


def canvas_size() -> Vec2:
    """Return the total size of _canvas."""
    return _canvas.realsize


def window_size() -> Vec2:
    """Return the size of the window (visible part of the _canvas)."""
    return Vec2(_canvas.GetSize())


def window_position() -> Vec2:
    """Return the position of the topleft corner on the _canvas."""
    return Vec2(_canvas.CalcUnscrolledPosition(0, 0))


def get_application_position() -> Vec2:
    """ Return the absolute position of thetop left corner of the applcition"""
    return Vec2(*_controller.get_application_position())


def canvas_scale() -> float:
    """Return the zoom scale of the _canvas."""
    return cstate.scale


def zoom_level() -> int:
    """The zoom level of the _canvas (Ranges from -10 to 10, with 0 being the default zoom).

    This is a discrete value that corresponds to the zoom slider to the bottom-right of the _canvas
    window.
    """
    return _canvas.zoom_level


def set_zoom_level(level: int, anchor: Vec2):
    """Set the zoom level of the _canvas.

    See zoom_level() for more details.

    Args:
        level: The zoom level to set.
        anchor: A point on the window whose position will remain the same after zooming. E.g. when
                the user zooms by scrolling the mouse, the anchor is the center of the window.
    """
    _canvas.SetZoomLevel(level, anchor)


def _translate_node(node: Node) -> NodeData:
    """Translate Node (internal data structure for rkviewer) to NodeData (for API)"""
    # composite_shape can only be done when the Node is created outside of iodine and then passed
    # into it. Any Node obtained from iodine (or controller) must have its composite_shape populated
    assert node.composite_shape is not None
    return NodeData(
        id=node.id,
        net_index=node.net_index,
        position=node.position,
        size=node.size,
        comp_idx=node.comp_idx,
        index=node.index,
        floating_node=node.floatingNode,
        lock_node=node.lockNode,
        original_index=node.original_index,
        shape_index=node.shape_index,
        shape=copy.copy(node.composite_shape),
        concentration=node.concentration,
        node_name = node.node_name,
        node_SBO = node.node_SBO
    )


def _translate_reaction(reaction: Reaction) -> ReactionData:
    """Translate Reaction (internal data structure for rkviewer) to ReactionData (for API)"""
    return ReactionData(
        id=reaction.id,
        net_index=reaction.net_index,
        fill_color=_to_color(reaction.fill_color),
        line_thickness=reaction.thickness,
        sources=reaction.sources,
        targets=reaction.targets,
        rate_law=reaction.rate_law,
        index=reaction.index,
        center_pos=reaction.center_pos,
        using_bezier=reaction.bezierCurves,
        modifiers=reaction.modifiers,
        modifier_tip_style=reaction.modifier_tip_style,
    )


def _translate_compartment(compartment: Compartment) -> CompartmentData:
    """Translate Reaction (internal data structure for rkviewer) to ReactionData (for API)"""
    return CompartmentData(
        id=compartment.id,
        net_index=compartment.net_index,
        nodes=compartment.nodes,
        position=compartment.position,
        size=compartment.size,
        volume=compartment.volume,
        fill_color=_to_color(compartment.fill),
        border_color=_to_color(compartment.border),
        border_width=compartment.border_width,
        index=compartment.index
    )


def get_node_indices(net_index: int) -> Set[int]:
    """Get the set of node indices (immutable)."""
    return _controller.get_node_indices(net_index)


def get_reaction_indices(net_index: int) -> Set[int]:
    """Get the set of reaction indices (immutable)."""
    return _controller.get_reaction_indices(net_index)


def get_compartment_indices(net_index: int) -> Set[int]:
    """Get the set of compartment indices (immutable)."""
    return _controller.get_compartment_indices(net_index)


def get_nodes(net_index: int) -> List[NodeData]:
    """
    Returns the list of all nodes in a network.

    Note:
        Modifying elements of this list will not update the _canvas.

    Returns:
        The list of nodes.
    """
    return [_translate_node(n) for n in _controller.get_list_of_nodes(net_index)]


def node_count(net_index: int) -> int:
    """
    Returns the number of nodes in the given network.
    """
    return len(get_nodes(net_index))


def get_reactions(net_index: int) -> List[ReactionData]:
    """
    Returns the list of all reactions in a network.

    Note:
        Modifying elements of this list will not update the _canvas.

    Returns:
        The list of reactions.
    """
    return [_translate_reaction(r) for r in _controller.get_list_of_reactions(net_index)]


def reaction_count(net_index: int) -> int:
    """
    Returns the number of reactions in the given network.
    """
    return len(get_reactions(net_index))


def get_compartments(net_index: int) -> List[CompartmentData]:
    """
    Returns the list of all compartments in a network.

    Note:
        Modifying elements of this list will not update the _canvas.

    Returns:
        The list of compartments.
    """
    return [_translate_compartment(c) for c in _controller.get_list_of_compartments(net_index)]


def compartments_count(net_index: int) -> int:
    """
    Returns the number of compartments in the given network.
    """
    return len(get_compartments(net_index))


def set_compartment_of_node(net_index: int, node_index: int, comp_index: int):
    """
    Move the node to the given compartment. Set comp_index to -1 to move it to the base compartment.
    """
    _controller.set_compartment_of_node(net_index, node_index, comp_index)


def get_compartment_of_node(net_index: int, node_index: int) -> int:
    """Return the compartment that the node is in, or -1 if it is in the base compartment."""
    return _controller.get_compartment_of_node(net_index, node_index)


def get_nodes_in_compartment(net_index: int, comp_index: int) -> List[int]:
    """Return the list node indices in the given compartment."""
    return _controller.get_nodes_in_compartment(net_index, comp_index)


def selected_nodes() -> List[NodeData]:
    """
    Returns the list of selected nodes.

    Note:
        Modifying elements of this list will not update the _canvas.

    Returns:
        The list of selected nodes.

    """
    return [_translate_node(n) for n in _canvas.GetSelectedNodes(copy=True)]


def selected_node_indices() -> Set[int]:
    """
    Returns the set of indices of the selected nodes.

    Returns:
        The set of selected nodes' indices.
    """
    return _canvas.sel_nodes_idx.item_copy()


def selected_reaction_indices() -> Set[int]:
    """
    Returns the set of indices of the selected reactions.

    Returns:
        The set of selected reactions' indices.
    """
    return _canvas.sel_reactions_idx.item_copy()


def get_node_by_index(net_index: int, node_index: int) -> NodeData:
    """
    Given an index, return the node that it corresponds to.

    Args:
        net_index (int): The network index.
        node_index (int): The node index.

    Returns:
        The node that corresponds to the given indices.
    """
    return _translate_node(_controller.get_node_by_index(net_index, node_index))


def get_reaction_by_index(net_index: int, reaction_index: int) -> ReactionData:
    """
    Given an index, return the reaction that it corresponds to.

    Args:
        net_index (int): The network index.
        reaction_index (int): The reaction index.

    Returns:
        The reaction that corresponds to the given indices.
    """
    return _translate_reaction(_controller.get_reaction_by_index(net_index, reaction_index))


def get_compartment_by_index(net_index: int, comp_index: int) -> CompartmentData:
    """
    Given an index, return the compartment that it corresponds to.

    Args:
        net_index (int): The network index.
        comp_index (int): The compartment index.

    Returns:
        The node that corresponds to the given indices.
    """
    return _translate_compartment(_controller.get_compartment_by_index(net_index, comp_index))


def delete_node(net_index: int, node_index: int) -> bool:
    """Delete a node with the given index in the given network.

    If the node does not exist, return False; otherwise return True. This method does not throw
    an error when the given node is missing, because the user may potentially be deleing nodes
    in a loop, and if an original node is deleted before its aliases, when the alias is reached
    it would no longer be in the network.

    If you want to make certain that a node does exist, use the return value of this function.

    Args:
        net_index: The network index.
        node_index: The node index.

    Returns:
        True if and only if a node was deleted.

    Raises:
        NetIndexError: If the given network does not exist
        NodeNotFreeError: If the given node is part of a reaction.
    """
    return _controller.delete_node(net_index, node_index)


def delete_reaction(net_index: int, reaction_index: int):
    """Delete a reaction with the given index in the given network.

    Args:
        net_index: The network index.
        reaction_index: The reaction index.

    Raises:
        NetIndexError:
        ReactionIndexError: If the given reaction does not exist in the network.
    """
    _controller.delete_reaction(net_index, reaction_index)


def delete_compartment(net_index: int, comp_index: int):
    """Delete a node with the given index in the given network.

    Nodes that are within this compartment are dropped to the base compartment (index -1).

    Args:
        net_index: The network index.
        comp_index: The compartment index.

    Raises:
        NetIndexError:
        CompartmentIndexError: If the given node does not exist in the network.
    """
    _controller.delete_compartment(net_index, comp_index)

def set_parameter_value(net_index: int, param_id: str, param_value: float):
    """
    Adds a parameter to a model, or updates parameter value if model already contains parameter
    """
    _controller.set_network_parameter(net_index, param_id, param_value)

def get_parameters(net_index: int):
    return _controller.get_network_parameters(net_index).copy()

def remove_parameter(net_index: int, param_id: str):
    _controller.remove_network_parameter(net_index, param_id)

def clear_parameters(net_index: int):
    params = _controller.get_network_parameters(net_index)
    for p in params.copy():
        _controller.remove_network_parameter(net_index, p)



def add_compartment(net_index: int, id: str, fill_color: Color = None, border_color: Color = None,
                    border_width: float = None, position: Vec2 = None, size: Vec2 = None,
                    volume: float = None, nodes: List[int] = None) -> int:
    """
    Adds a compartment.

    The Compartment indices are assigned in increasing order, regardless of deletion.

    Args:
        net_index: The network index
        compartment: the Compartment to add

    Returns:
        The index of the compartment that was added.
    """
    if fill_color is None:
        fill_color = _to_color(get_theme('comp_fill'))

    if border_color is None:
        border_color = _to_color(get_theme('comp_border'))

    if border_width is None:
        border_width = get_theme('comp_border_width')

    if position is None:
        position = Vec2()

    if size is None:
        size = Vec2(get_setting('min_comp_width'), get_setting('min_comp_height'))

    if volume is None:
        volume = 1

    if nodes is None:
        nodes = list()

    compartment = Compartment(
        id=id,
        net_index=net_index,
        nodes=nodes,
        volume=volume,
        position=position,
        size=size,
        fill=_to_wxcolour(fill_color),
        border=_to_wxcolour(border_color),
        border_width=border_width,
        index=-1
    )
    return _controller.add_compartment_g(net_index, compartment)


def add_node(net_index: int, id: str, fill_color: Color = None, border_color: Color = None,
             border_width: float = None, position: Vec2 = None, size: Vec2 = None, comp_idx: int = -1,
             floating_node: bool = True, lock_node: bool = False, shape_index: int = 0,
             concentration: float = 0.0, node_name: str = '', node_SBO: str = '') -> int:
    """Adds a node to the given network.

    The node indices are assigned in increasing order, regardless of deletion.

    Args:
        net_index: The network index.
        id: The ID of the node.
        fill_color: The fill color of the node, or leave as None to use current theme.
        border_color: The border color of the node, or leave as None to use current theme.
        border_width: The border width of the node, or leave as None to use current theme.
        position: The position of the node, or leave as None to use default, (0, 0).
        size: The size of the node, or leave as None to use default, (0, 0).
        comp_idx: The index of the compartment that the node is in, default as -1.
        shape_index: The index of the CompositeShape of the node. 0 (rectangle) by default.
        concentration: The concentration of the node, or leave as None to use default, 0.0.
        node_name: The name of the node.
        node_SBO: The SBO of the node.

    Returns:
        The index of the node that was added.
    """
    if fill_color is None:
        fill_color = _to_color(get_theme('node_fill'))

    if border_color is None:
        border_color = _to_color(get_theme('node_border'))

    if border_width is None:
        border_width = get_theme('node_border_width')

    if position is None:
        position = Vec2()

    if size is None:
        size = Vec2(get_theme('node_width'), get_theme('node_height'))

    node = Node(
        id,
        net_index,
        pos=position,
        size=size,
        floatingNode=floating_node,
        lockNode=lock_node,
        shape_index=shape_index,
        concentration=concentration,
        node_name = node_name,
        node_SBO = node_SBO,
        comp_idx = comp_idx
    )
    with group_action():
        nodei = _controller.add_node_g(net_index, node)
        _controller.set_node_fill_rgb(net_index, nodei, _to_wxcolour(fill_color))
        _controller.set_node_fill_alpha(net_index, nodei, fill_color.a)
        _controller.set_node_border_rgb(net_index, nodei, _to_wxcolour(border_color))
        _controller.set_node_border_alpha(net_index, nodei, border_color.a)
        _controller.set_node_border_width(net_index, nodei, border_width)
        _controller.set_node_concentration(net_index, nodei, concentration)
        _controller.set_node_name(net_index, nodei, node_name)
        _controller.set_node_SBO(net_index, nodei, node_SBO)
    return nodei


def add_alias(net_index: int, original_index: int, position: Vec2 = None, size: Vec2 = None):
    """Adds an alias node to the network.

    The node indices are assigned in increasing order, regardless of deletion.

    Args:
        net_index: The network index.
        original_index: The index of the original node, from which to create an alias
        position: The position of the alias, or leave as None to use default, (0, 0).
        size: The size of the alias, or leave as None to use default, (0, 0).

    Returns:
        The index of the alias that was added.
    """
    position = position or Vec2()
    size = size or Vec2(get_theme('node_width'), get_theme('node_height'))

    with group_action():
        aliasi = _controller.add_alias_node(net_index, original_index, position, size)

    return aliasi


def move_node(net_index: int, node_index: int, position: Vec2, allowNegativeCoordinates: bool = False):
    """Change the position of a node."""
    _controller.move_node(net_index, node_index, position, allowNegativeCoordinates)


def move_compartment(net_index: int, comp_index: int, position: Vec2):
    """Change the position of a compartment."""
    _controller.move_compartment(net_index, comp_index, position)


def resize_node(net_index: int, node_index: int, size: Vec2):
    """Change the size of a node."""
    _controller.set_node_size(net_index, node_index, size)


# TODO add "cosmetic" versions of these functions, where changes made to _controller are not added
# to the history stack. This requires _controller to have "programmatic group" feature, i.e. actions
# performed inside such groups are not recorded. programmatic groups nested within group operations
# should be ignored.
def update_node(net_index: int, node_index: int, id: str = None, fill_color: Color = None,
                border_color: Color = None, border_width: float = None, position: Vec2 = None,
                size: Vec2 = None, floating_node: bool = True, lock_node: bool = False,
                shape_index: int = None, concentration: float = None, node_name: str = None,
                node_SBO: str = None):
    """
    Update one or multiple properties of a node.

    Args:
        net_index: The network index.
        node_index: The node index of the node to modify.
        id: If specified, the new ID of the node.
        fill_color: If specified, the new fill color of the node.
        border_color: If specified, the new border color of the node.
        border_width: If specified, the new border width of the node.
        position: If specified, the new position of the node.
        size: If specified, the new size of the node.
        floating_node: If specified, the floating status of the node.
        lock_node: If specified, whether the node is locked.
        shape_index: If specified, the new shape of the node.
        concentration: If specified, the new concentration of the node.
        node_name: If specified, the new node name.
        node_SBO: If specified, the new node SBO.

    Note:
        This is *not* an atomic function, meaning if we failed to set one specific property, the
        previous changes to model in this function will not be undone, even after the exception
        is caught. To go around that, make one calls to update_node() for each property instead.

        Also note the behavior if the given node_index refers to an alias node.
        The properties 'position', 'size', and 'lock_node' pertain to the alias node itself.
        But all other properties pertain to the original node that the alias refers to. For example,
        if one sets the 'position' of an alias node, the position of the alias is updated. But if
        one sets the 'id' of an alias node, the ID of the original node is modified (and that of
        the alias node is updated to reflect that).

    Raises:
        ValueError: If ID is empty or if any one of border_width, position, and size is out of
                    range.
        NetIndexError:
        NodeIndexError:
    """
    # Make sure this node exists
    old_node = get_node_by_index(net_index, node_index)
    # Validate
    # Check ID not empty
    if id is not None and len(id) == 0:
        raise ValueError('id cannot be empty')

    # # Check border at least 0
    # if border_width is not None and border_width < 0:
    #     raise ValueError("border_width must be at least 0")

    # # Check position at least 0
    # if position is not None and (position.x < 0 or position.y < 0):
    #     raise ValueError("position cannot have negative coordinates, but got '{}'".format(position))

    # # Check size at least 0
    # if size is not None and (size.x < 0 or size.y < 0):
    #     raise ValueError("size cannot have negative dimensions, but got '{}'".format(size))

    # Check within bounds
    if position is not None or size is not None:
        pos = position if position is not None else old_node.position
        sz = size if size is not None else old_node.size
        botright = pos + sz
        if botright.x > _canvas.realsize.x or botright.y > _canvas.realsize.y:
            raise ValueError('Invalid position and size combination ({} and {}): bottom right '
                             'corner exceed _canvas boundary {}', pos, sz, _canvas.realsize)

    with group_action():
        if id is not None:
            _controller.rename_node(net_index, node_index, id)
        if fill_color is not None:
            _controller.set_node_fill_rgb(net_index, node_index, _to_wxcolour(fill_color))
            _controller.set_node_fill_alpha(net_index, node_index, fill_color.a)
        if border_color is not None:
            _controller.set_node_border_rgb(net_index, node_index, _to_wxcolour(border_color))
            _controller.set_node_border_alpha(net_index, node_index, border_color.a)
        if border_width is not None:
            _controller.set_node_border_width(net_index, node_index, border_width)
        if position is not None:
            _controller.move_node(net_index, node_index, position)
        if size is not None:
            _controller.set_node_size(net_index, node_index, size)
        if floating_node is not None:
            _controller.set_node_floating_status(net_index, node_index, floating_node)
        if lock_node is not None:
            _controller.set_node_locked_status(net_index, node_index, lock_node)
        if shape_index is not None:
            _controller.set_node_shape_index(net_index, node_index, shape_index)

        if concentration is not None:
            if concentration < 0.0:
                raise ValueError('Invalid concentration value. Concentration must not be negative.')
            else:
                _controller.set_node_concentration(net_index, node_index, concentration)

        if node_name is not None:
            _controller.set_node_name(net_index, node_index, node_name)
        if node_SBO is not None:
            _controller.set_node_SBO(net_index, node_index, node_SBO)


def set_node_shape_property(net_index: int, node_index: int, primitive_index: int,
                            prop_name: str, prop_value: Any):
    '''Set a property of the node's composite shape, e.g. fill color.

    NOTE specify -1 for `primitive_index` to modify the text primitive of the node.

    For this, one needs to specify a particular primitive inside the composite shape. For example,
    if a node is composed of two circles, there are two circle primitives (CirclePrim) inside
    the node's shape. One can only update the property of one primitive at a time, e.g.
    primitive_index = 0 for the first circle, and primitive_index = 1 for the second.

    One also must specify the property name (prop_name), which is a string. Some common property
    names are 'fill_color', 'border_color', 'border_width'. Each particular primitive may have
    other properties. For more details, see the subclasses of Primitive in rkviewer/canvas/data.py.

    As an example, for node with index 5 in network 0 with two circles in its CompositeShape, to set
    the fill color of circle 1 to red, do
    `set_node_shape_property(0, 5, 1, 'fill_color', Color(255, 0, 0)).

    Note that an error will be thrown if there is a mismatch between the supplied prop_value and
    the expected type. For example, you cannot assign 1 to 'fill_color', only objects of type Color.
    Also an error will be thrown if the primitive index is out of bounds on the current shape that
    the node has. Therefore, you should make sure that the node has the shape (or
    at least the primitive count and primitive properties) that you expect before calling this
    function.

    Args:
        net_index:          The network index.
        node_index:         The index of the node.
        primitive_index:    The index of the shape primitive whose property to update. To set the
                            text properties of the node, specify -1 here.
        prop_name:          The name of the property whose value to set.
        prop_value:         The new value of the property.
    '''
    _controller.set_node_primitive_property(net_index, node_index, primitive_index, prop_name,
                                            prop_value)


def compute_centroid(net_index: int, reactants: List[int], products: List[int]):
    """Compute the centroid of the given sets of reactant and product nodes.

    The centroid is used as the position of the center circle of reactions.

    Args:
        net_index: The network index.
        reactants: The list of reactant node indices.
        products: The list of product node indices.
    """
    sources = [_controller.get_node_by_index(net_index, nodei) for nodei in reactants]
    targets = [_controller.get_node_by_index(net_index, nodei) for nodei in products]
    s_rects = [n.rect for n in sources]
    t_rects = [n.rect for n in targets]
    return data.compute_centroid(s_rects + t_rects)


def default_handle_positions(net_index: int, reaction_index: int) -> List[Vec2]:
    """Return the default Bezier handle positions for the given reaction.

    See Reaction for more details on the format of this list.

    Args:
        net_index: The network index.
        reaction_index: The index of the reaction.
    """
    rxn = get_reaction_by_index(net_index, reaction_index)
    sources = [_controller.get_node_by_index(net_index, nodei) for nodei in rxn.sources]
    targets = [_controller.get_node_by_index(net_index, nodei) for nodei in rxn.targets]
    return _default_handle_positions(rxn.real_center, sources, targets)


def _set_handle_positions(reaction: Reaction, handle_positions: List[Vec2]):
    """Helper to set handle positions."""
    assert len(handle_positions) == len(reaction.sources) + len(reaction.targets) + 1
    _controller.set_center_handle(reaction.net_index, reaction.index, handle_positions[0])
    for (gi, nodei), pos in zip(gchain(reaction.sources, reaction.targets),
                                handle_positions[1:]):
        if gi == 0:
            _controller.set_src_node_handle(reaction.net_index, reaction.index, nodei, pos)
        else:
            _controller.set_dest_node_handle(reaction.net_index, reaction.index, nodei, pos)


def add_reaction(net_index: int, id: str, reactants: List[int], products: List[int],
                 fill_color: Color = None, line_thickness: float = None,
                 rate_law: str = '', handle_positions: List[Vec2] = None,
                 center_pos: Vec2 = None, use_bezier: bool = True, 
                 modifiers: Set[int] = None) -> int:
    """
    Adds a reaction.

    The reaction indices are assigned in increasing order, regardless of deletion. See
    ReactionData for more documentation on the fields.

    Args:
        net_index: The network index.
        id: The ID of the reaction.
        reactants: The list of reactant node indices.
        products: The list of product node indices.
        fill_color: The fill color of the reaction line, or leave as None to use current theme.
        line_thickness: The thickness of the reaction line, or leave as None to use current theme.
        rate_law: The reaction rate law; defaults to empty string.
        handle_positions: The initial positions of the Bezier handles
        center_pos: The position of the reaction center. If None, the center position will be
                    automatically set as the centroid of all the species and will dynamically move
                    as nodes are moved.
        use_bezier: If specified, whether to use Bezier curves when drawing the reaction. If False,
                    simply use straight lines.
        modifiers: The set of reaction of modifiers, defaulting to None. If None, no modifiers will be added.
    Returns:
        The index of the reaction that was added.
    """
    if fill_color is None:
        fill_color = _to_color(get_theme('reaction_fill'))

    if line_thickness is None:
        line_thickness = get_theme('reaction_line_thickness')

    auto_init_handles = False
    if handle_positions is None:
        auto_init_handles = True
        handle_positions = [Vec2() for _ in range(1 + len(reactants) + len(products))]
    else:
        if len(handle_positions) != 1 + len(reactants) + len(products):
            raise ValueError('The number of handles must equal to 1 + len(reactants) + '
                             'len(products)')

    reaction = Reaction(
        id,
        net_index,
        sources=reactants,
        targets=products,
        fill_color=_to_wxcolour(fill_color),
        line_thickness=line_thickness,
        rate_law=rate_law,
        handle_positions=handle_positions,
        center_pos=center_pos,
        bezierCurves=use_bezier,
    )

    with group_action():
        reai = _controller.add_reaction_g(net_index, reaction)
        # HACK set default handle positions. This should be computed by default_handle_positions()
        # before constructing the Reaction object, but right now it only accepts a list of nodes. In
        # the future modify default_handle_positions() to accept four lists: reactant rectangles and
        # indices, and product rectangles and indices, since these are the only requisite parameters.
        if auto_init_handles:
            handle_positions = default_handle_positions(net_index, reai)
            reaction.index = reai
            _set_handle_positions(reaction, handle_positions)
        if modifiers is not None:
            _controller.set_reaction_modifiers(net_index, reai, modifiers)

    return reai


def update_reaction(net_index: int, reaction_index: int, id: str = None,
                    fill_color: Color = None, thickness: float = None, ratelaw: str = None,
                    handle_positions: List[Vec2] = None,
                    center_pos: Union[Optional[Vec2], CustomNone] = CustomNone(),
                    use_bezier: bool = None, modifiers: Set[int] = None, 
                    modifier_tip_style: ModifierTipStyle = ModifierTipStyle.CIRCLE):
    """
    Update one or multiple properties of a reaction.

    Args:
        net_index: The network index.
        reaction_index: The reaction index of the reaction to modify.
        id: If specified, the new ID of the reaction.
        fill_color: If specified, the new fill color of the reaction.
        thickness: If specified, the thickness of the reaction.
        ratelaw: If specified, the rate law of the reaction.
        handle_positions: If specified, the list of handles of the reaction. See add_reaction() for
                          details on the format.
        center_pos: The position of the reaction center. If None, the center position will be
                    automatically set as the centroid of all the species and will dynamically move
                    as nodes are moved.
        use_bezier: If specified, whether to use Bezier curves when drawing the reaction. If False,
                    simply use straight lines.
        modifiers: If specified, the set of reaction modifiers
        modifier_tip_style The modifier tip style.

    Note:
        This is *not* an atomic function, meaning if we failed to set one specific property, the
        previous changes to model in this function will not be undone, even after the exception
        is caught. To go around that, make one calls to update_node() for each property instead.

    Raises:
        ValueError: If ID is empty or if thickness is less than zero.
        NetIndexError:
        ReactionIndexError:
    """
    # The reaction to update. Will fail here if it does not exist.
    reaction = _controller.get_reaction_by_index(net_index, reaction_index)
    # Validate
    # Check ID not empty
    if id is not None and len(id) == 0:
        raise ValueError('id cannot be empty')

    with group_action():
        if id is not None:
            _controller.rename_reaction(net_index, reaction_index, id)
        if fill_color is not None:
            _controller.set_reaction_fill_rgb(net_index, reaction_index, _to_wxcolour(fill_color))
            _controller.set_reaction_fill_alpha(net_index, reaction_index, fill_color.a)
        if thickness is not None:
            _controller.set_reaction_line_thickness(net_index, reaction_index, thickness)
        if ratelaw is not None:
            _controller.set_reaction_ratelaw(net_index, reaction_index, ratelaw)
        if handle_positions is not None:
            _set_handle_positions(reaction, handle_positions)
        if not isinstance(center_pos, CustomNone):
            _controller.set_reaction_center(net_index, reaction_index, center_pos)
        if use_bezier is not None:
            _controller.set_reaction_bezier_curves(net_index, reaction_index, use_bezier)
        if modifier_tip_style is not None:
            _controller.set_modifier_tip_style(net_index, reaction_index, modifier_tip_style)
        if modifiers is not None:
            _controller.set_reaction_modifiers(net_index, reaction_index, modifiers)


def get_selected_node_indices(net_index: int) -> Set[int]:
    """Return the set of selected node indices."""
    return _canvas.sel_nodes_idx.item_copy()


def get_selected_reaction_indices() -> Set[int]:
    """Return the set of selected reaction indices."""
    return _canvas.sel_reactions_idx.item_copy()


def get_selected_compartment_indices() -> Set[int]:
    """Return the set of selected compartment indices."""
    return _canvas.sel_compartments_idx.item_copy()


def get_reactions_as_reactant(net_index: int, node_index: int) -> Set[int]:
    """Get the set of reactions (indices) of which this node is a reactant."""
    return _controller.get_reactions_as_reactant(net_index, node_index)


def get_reactions_as_product(net_index: int, node_index: int) -> Set[int]:
    """Get the set of reactions (indices) of which this node is a product."""
    return _controller.get_reactions_as_product(net_index, node_index)


def is_reactant(net_index: int, node_index: int, reaction_index: int) -> bool:
    """Return whether the given node is a reactant of the given reaction.

    This runs linearly to number of reactants of the given reaction. If your reaction
    is very very large, then construct a set from its reactants and test for membership manually.

    TODO:
        This can be implemented to run in constant time by implementing an iodine function
        that tests reaction_index in network.srcMap[node_index].
    """
    reaction = _controller.get_reaction_by_index(net_index, reaction_index)
    return node_index in reaction.sources


def is_product(net_index: int, node_index: int, reaction_index: int) -> bool:
    """Return whether the given node is a product of the given reaction.

    This runs linearly to the number of products of the given reaction. If your reaction
    is very very large, then construct a set from its products and test for membership manually.
    """
    reaction = _controller.get_reaction_by_index(net_index, reaction_index)
    return node_index in reaction.targets


def update_compartment(net_index: int, comp_index: int, id: str = None,
                       fill_color: Color = None, border_color: Color = None,
                       border_width: float = None, volume: float = None,
                       position: Vec2 = None, size: Vec2 = None):
    """
    Update one or multiple properties of a compartment.

    Args:
        net_index: The network index.
        comp_index: The compartment index of the compartment to modify.
        id: If specified, the new ID of the node.
        fill_color: If specified, the new fill color of the compartment.
        border_color: If specified, the new border color of the compartment.
        border_width: If specified, the new border width of the compartment.
        volume: If specified, the new volume of the compartment.
        position: If specified, the new position of the compartment.
        size: If specified, the new size of the compartment.

    Raises:
        ValueError: If ID is empty or if any one of border_width, position, and size is out of
                    range.
        NetIndexError:
        CompartmentIndexError:

    Note:
        This is *not* an atomic function, meaning if we failed to set one specific property, the
        previous changes to model in this function will not be undone, even after the exception
        is caught. To go around that, make one calls to update_node() for each property instead.
    """
    old_comp = get_compartment_by_index(net_index, comp_index)
    # Validate
    # Check ID not empty
    if id is not None and len(id) == 0:
        raise ValueError('id cannot be empty')

    # # Check border at least 0
    # if border_width is not None and border_width < 0:
    #     raise ValueError("border_width must be at least 0")

    # # Check position at least 0
    # if position is not None and (position.x < 0 or position.y < 0):
    #     raise ValueError("position cannot have negative coordinates, but got '{}'".format(position))

    # # Check size at least 0
    # if size is not None and (size.x < 0 or size.y < 0):
    #     raise ValueError("size cannot have negative coordinates, but got '{}'".format(size))

    # Check within bounds
    if position is not None or size is not None:
        pos = position if position is not None else old_comp.position
        sz = size if size is not None else old_comp.size
        botright = pos + sz
        if botright.x > _canvas.realsize.x or botright.y > _canvas.realsize.y:
            raise ValueError('Invalid position and size combination ({} and {}): bottom right '
                             'corner exceed _canvas boundary {}', pos, sz, _canvas.realsize)

    with group_action():
        if id is not None:
            _controller.rename_compartment(net_index, comp_index, id)
        if fill_color is not None:
            _controller.set_compartment_fill(net_index, comp_index, _to_wxcolour(fill_color))
        if border_color is not None:
            _controller.set_compartment_border(net_index, comp_index, _to_wxcolour(border_color))
        if border_width is not None:
            _controller.set_compartment_border_width(net_index, comp_index, border_width)
        if volume is not None:
            _controller.set_compartment_volume(net_index, comp_index, volume)
        if position is not None:
            _controller.move_compartment(net_index, comp_index, position)
        if size is not None:
            _controller.set_compartment_size(net_index, comp_index, size)


def get_reactant_stoich(net_index: int, reaction_index: int, node_index: int) -> float:
    """Returns the stoichiometry of a reactant node.

    Args:
        net_index: The network index
        reaction_index: The index of the reaction.
        node_index: The index of the node which must be a reactant of the reaction.

    Raises:
        NetIndexError:
        ReactionIndexError:
        NodeIndexError: If the given node index does not match any existing node.
        ValueError: If the given node index exists but is not a reactant of the reaction.
    """
    return _controller.get_src_node_stoich(net_index, reaction_index, node_index)


def set_reactant_stoich(net_index: int, reaction_index: int, node_index: int, stoich: int):
    """
    Set the stoichiometry of a reactant node.

    Args:
        net_index: The network index
        reaction_index: The index of the reaction.
        node_index: The index of the node which must be a reactant of the reaction.
        stoich: The new stoichiometry value.

    Raises:
        NetIndexError:
        ReactionIndexError:
        NodeIndexError: If the given node index does not match any existing node.
        ValueError: If the given node index exists but is not a reactant of the reaction.
    """
    _controller.set_src_node_stoich(net_index, reaction_index, node_index, stoich)


def get_product_stoich(net_index: int, product_index: int, node_index: int) -> float:
    """Returns the stoichiometry of a product node.

    Args:
        net_index: The network index.
        reaction_index: The index of the reaction.
        node_index: The index of the node which must be a product of the reaction.

    Raises:
        NetIndexError:
        ReactionIndexError:
        NodeIndexError: If the given node index does not match any existing node.
        ValueError: If the given node index exists but is not a product of the reaction.
    """
    return _controller.get_dest_node_stoich(net_index, product_index, node_index)


def set_product_stoich(net_index: int, reaction_index: int, node_index: int, stoich: int):
    """Sets the product's stoichiometry.

    Args:
        net_index: The network index.
        reaction_index: The index of the reaction.
        node_index: The index of the node which must be a product of the reaction.
        stoich: The new stoichiometry value.

    Raises:
        NetIndexError:
        ReactionIndexError:
        NodeIndexError: If the given node index does not match any existing node.
        ValueError: If the given node index exists but is not a reactant of the reaction.
    """
    _controller.set_dest_node_stoich(net_index, reaction_index, node_index, stoich)


def get_reaction_node_handle(net_index: int, reaction_index: int, node_index: int,
                             is_source: bool) -> Vec2:
    """Get the position of the reaction Bezier handle associated with a node.

    Args:
        net_index: The network index.
        reaction_index: The reaction index.
        node_index: The index of the node whose Bezier handle position to get.
        is_source: Whether the node is a source node. If a node is both a source and a target node,
                   it would have two Bezier handles, hence the distinction.

    Raises:
        NetIndexError:
        ReactionIndexError:
        NodeIndexError: If the given node index is not found
        ValueError: If the given node is found but it is not an indicated node of the reaction.
    """
    if is_source:
        return _controller.get_src_node_handle(net_index, reaction_index, node_index)
    else:
        return _controller.get_dest_node_handle(net_index, reaction_index, node_index)


def set_reaction_node_handle(net_index: int, reaction_index: int, node_index: int, is_source: bool,
                             handle_pos: Vec2):
    """Set the position of the reaction Bezier handle associated with a node.

    Args:
        net_index: The network index.
        reaction_index: The reaction index.
        node_index: The index of the node whose Bezier handle to move.
        is_source: Whether the node is a source node. If a node is both a source and a target node,
                   it would have two Bezier handles, hence the distinction.
        handle_pos: The new position of the Bezier handle.

    Raises:
        NetIndexError:
        ReactionIndexError:
        NodeIndexError: If the given node index is not found
        ValueError: If the given node is found but it is not an indicated node of the reaction.
    """
    if is_source:
        _controller.set_src_node_handle(net_index, reaction_index, node_index, handle_pos)
    else:
        _controller.set_dest_node_handle(net_index, reaction_index, node_index, handle_pos)


def get_reaction_center_handle(net_index: int, reaction_index: int) -> Vec2:
    """Get the position of the Bezier handle at the center of the given reaction.

    Args:
        net_index: The network index.
        reaction_index: The index of the reaction whose center Bezier handle position to get.
        handle_pos: The new position of the Bezier handle.

    Raises:
        NetIndexError:
        ReactionIndexError:
    """
    return _controller.get_center_handle(net_index, reaction_index)


def set_reaction_center_handle(net_index: int, reaction_index: int, handle_pos: Vec2):
    """Set the position of the Bezier handle at the center of the given reaction.

    Args:
        net_index: The network index.
        reaction_index: The index of the reaction whose center Bezier handle to move.
        handle_pos: The new position of the Bezier handle.

    Raises:
        NetIndexError:
        ReactionIndexError:
    """
    _controller.set_center_handle(net_index, reaction_index, handle_pos)


def get_arrow_tip() -> ArrowTip:
    """
    Gets the current arrow tip.
    """
    return cstate.arrow_tip.clone()


def get_default_arrow_tip() -> ArrowTip:
    """
    Gets the default arrow tip.
    """
    return ArrowTip(copy.copy(DEFAULT_ARROW_TIP))


def set_arrow_tip(value: ArrowTip):
    """
    Set the arrow tip to a given one.

    Args:
        The given ArrowTip to set to.
    """
    cstate.arrow_tip = value.clone()
    _canvas.ArrowTipChanged()
    # TODO save to settings; pending https://github.com/evilnose/PyRKViewer/issues/16


def get_network_bounds(net_index: int):
    """Return the rectangular bounds of a network."""
    # NOTE currently hardcoded
    return _canvas.realsize


def update_canvas():
    """Update the canvas immediately. Useful if you want to redraw before a group action ends.
    """
    _controller.update_view()


def translate_network(net_index: int, offset: Vec2, check_bounds: bool = True) -> bool:
    """Translate the given network by a fixed amount.

    Args:
        net_index: The network index.
        offset: The offset to shift the network.
        check_bounds: If True, check to ensure that everything will be within bounds after the
                      shift. Defaults to True, and this is recommended unless you have already
                      performed that check yourself.
    """
    nodes = get_nodes(net_index)
    comps = get_compartments(net_index)
    if check_bounds:
        bounds = get_network_bounds(net_index)
        for node in nodes:
            newpos = node.position + offset
            if newpos.x < 0 or newpos.y < 0 or newpos.x + node.size.x >= bounds.x or \
                    newpos.y + node.size.y >= bounds.y:
                return False
        for comp in comps:
            newpos = comp.position + offset
            if newpos.x < 0 or newpos.y < 0 or newpos.x + comp.size.x >= bounds.x or \
                    newpos.y + comp.size.y >= bounds.y:
                return False

    with group_action():
        for node in nodes:
            move_node(net_index, node.index, node.position + offset)
        for comp in comps:
            move_compartment(net_index, comp.index, comp.position + offset)
        for reaction in _controller.get_list_of_reactions(net_index):
            handles = reaction.handles
            new_handle_pos = [reaction.src_c_handle.tip +
                              offset] + [h.tip + offset for h in handles]
            new_center_pos = None
            if reaction.center_pos is not None:
                new_center_pos = reaction.center_pos + offset
            update_reaction(net_index, reaction.index,
                            handle_positions=new_handle_pos, center_pos=new_center_pos)

    return True

