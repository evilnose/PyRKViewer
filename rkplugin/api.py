"""
API for the RKViewer GUI and model. Allows viewing and modifying the network model.
"""

# pylint: disable=maybe-no-member
#from rkviewer.mvc import NetIndexError
from rkviewer.canvas.geometry import Rect, within_rect
from rkviewer.config import DEFAULT_ARROW_TIP
import wx
import copy
from contextlib import contextmanager
from rkviewer.mvc import IController
from typing import List, Optional, Set, Tuple
from rkviewer.controller import Controller
from rkviewer.canvas.canvas import Canvas
from rkviewer.canvas import data
from rkviewer.canvas.state import cstate, ArrowTip
from rkviewer import config

Node = data.Node
Reaction = data.Reaction
Compartment = data.Compartment
Vec2 = data.Vec2
theme = config.theme
settings = config.settings

# TODO allow modification of theme and setting in the GUI

_canvas: Optional[Canvas] = None
_controller: Optional[IController] = None


def init_api(canvas: Canvas, controller: IController):
    """
    Initializes api.

    Args:
        Canvas (canvas) : On which you are working
        ICOntroller (controller): chosen controller
    """
    global _canvas, _controller
    _canvas = canvas
    _controller = controller


def uninit_api():
    global _canvas, _controller
    _controller.clear_network(0)
    _canvas = None
    _controller = None


def cur_net_index() -> int:
    return _canvas.net_index


@contextmanager
def group_action():
    """Context manager for doing a group operation in the controller, for undo/redo purposes.

    Examples:
        As shown here, calls to the API within the group_action context are considered to be
        within one single group as far as undoing/redoing is concerned.

        >>> with api.group_action():
        >>>     for node in some_node_list:
        >>>         api.update_node(...)
        >>>     api.update_reaction(...)
        >>> api.update_node(...)  # This is now a new action.

    """
    _controller.start_group()
    yield
    _controller.end_group()


def canvas_size() -> Vec2:
    """Return the total size of canvas."""
    return _canvas.realsize


def window_size() -> Vec2:
    """Return the size of the window (visible part of the canvas)."""
    return Vec2(_canvas.GetSize())


def window_position() -> Vec2:
    """Return the position of the topleft corner on the canvas."""
    return Vec2(_canvas.CalcUnscrolledPosition(0, 0))


def canvas_scale() -> float:
    """Return the zoom scale of the canvas."""
    return cstate.scale


def zoom_level() -> int:
    """The zoom level of the canvas (Ranges from -10 to 10, with 0 being the default zoom).

    This is a discrete value that corresponds to the zoom slider to the bottom-right of the canvas
    window.
    """
    return _canvas.zoom_level


def set_zoom_level(level: int, anchor: Vec2):
    """Set the zoom level of the canvas.
    
    See zoom_level() for more details.

    Args:
        level: The zoom level to set.
        anchor: A point on the window whose position will remain the same after zooming. E.g. when
                the user zooms by scrolling the mouse, the anchor is the center of the window.
    """
    _canvas.SetZoomLevel(level, anchor)


def get_nodes(net_index: int) -> List[Node]:
    """ 
    Returns the list of all nodes in a network.

    Note:
        Modifying elements of this list will not update the canvas.

    Returns:
        The list of nodes.
    """
    return _controller.get_list_of_nodes(net_index)


def node_count(net_index: int) -> int:
    """
    Returns the number of nodes in the given network.
    """
    return len(get_nodes(net_index))


def get_reactions(net_index: int) -> List[Reaction]:
    """ 
    Returns the list of all reactions in a network.

    Note:
        Modifying elements of this list will not update the canvas.

    Returns:
        The list of reactions.
    """
    return _controller.get_list_of_reactions(net_index)


def reaction_count(net_index: int) -> int:
    """
    Returns the number of reactions in the given network.
    """
    return len(get_reactions(net_index))


def get_compartments(net_index: int) -> List[Compartment]:
    """ 
    Returns the list of all compartments in a network.

    Note:
        Modifying elements of this list will not update the canvas.

    Returns:
        The list of compartments.
    """
    return _controller.get_list_of_compartments(net_index)


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


def selected_nodes() -> List[Node]:
    """ 
    Returns the list of selected nodes.

    Note:
        Modifying elements of this list will not update the canvas.

    Returns:
        The list of selected nodes.

    """
    return _canvas.GetSelectedNodes(copy=True)


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


def get_node_by_index(net_index: int, node_index: int) -> Node:
    """ 
    Given an index, return the node that it corresponds to.

    Args:  
        net_index (int): The network index.
        node_index (int): The node index.

    Returns:
        The node that corresponds to the given indices.
    """
    return _controller.get_node_by_index(net_index, node_index)


def get_reaction_by_index(net_index: int, reaction_index: int) -> Reaction:
    """ 
    Given an index, return the reaction that it corresponds to.

    Args:  
        net_index (int): The network index.
        reaction_index (int): The reaction index.

    Returns:
        The reaction that corresponds to the given indices.
    """
    return _controller.get_reaction_by_index(net_index, reaction_index)


def get_compartment_by_index(net_index: int, comp_index: int) -> Compartment:
    """ 
    Given an index, return the compartment that it corresponds to.

    Args:  
        net_index (int): The network index.
        comp_index (int): The compartment index.

    Returns:
        The node that corresponds to the given indices.
    """
    return _controller.get_compartment_by_index(net_index, comp_index)


def add_node(net_index: int, node: Node):
    """Adds a node to the given network.

    The node indices are assigned in increasing order, regardless of deletion.

    Args:  
        net_index: The network index.
        node: The Node to add.
    """
    _controller.add_node_g(net_index, node)


def delete_node(net_index: int, node_index: int):
    """Delete a node with the given index in the given network.

    Args:
        net_index: The network index.
        node_index: The node index.

    Raises:
        NetIndexError:
        NodeIndexError: If the given node does not exist in the network.
        NodeNotFreeError: If the given onde is part of a reaction.
    """
    _controller.delete_node(net_index, node_index)


def add_reaction(net_index: int, reaction: Reaction):
    """ 
    Adds a reaction.

    The reaction indices are assigned in increasing order, regardless of deletion.

    Args:  
        net_index: the index overall
        reaction: the Reaction to add
    """
    _controller.add_reaction_g(net_index, reaction)


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


def add_compartment(net_index: int, compartment: Compartment):
    """ 
    Adds a compartment.

    The Compartment indices are assigned in increasing order, regardless of deletion.

    Args:  
        net_index: the index overall
        compartment: the Compartment to add
    """
    _controller.add_compartment_g(net_index, compartment)


# TODO add "cosmetic" versions of these functions, where changes made to controller are not added
# to the history stack. This requires controller to have "programmatic group" feature, i.e. actions
# performed inside such groups are not recorded. programmatic groups nested within group operations
# should be ignored.
def update_node(net_index: int, node_index: int, id_: str = None, fill_color: wx.Colour = None,
                border_color: wx.Colour = None, border_width: float = None, position: Vec2 = None,
                size: Vec2 = None):
    """
    Update one or multiple properties of a node.

    Args:
        net_index: The network index.
        node_index: The node index of the node to modify.
        id_: If specified, the new ID of the node.
        fill_color: If specified, the new fill color of the node.
        border_color: If specified, the new border color of the node.
        border_width: If specified, the new border width of the node.
        position: If specified, the new position of the node.
        size: If specified, the new size of the node.

    Note:
        This is *not* an atomic function, meaning if we failed to set one specific property, the
        previous changes to model in this function will not be undone, even after the exception
        is caught. To go around that, make one calls to update_node() for each property instead.
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
    if id_ is not None and len(id_) == 0:
        raise ValueError('id_ cannot be empty')

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
                             'corner exceed canvas boundary {}', pos, sz, _canvas.realsize)

    with group_action():
        if id_ is not None:
            _controller.rename_node(net_index, node_index, id_)
        if fill_color is not None:
            _controller.set_node_fill_rgb(net_index, node_index, fill_color)
            _controller.set_node_fill_alpha(net_index, node_index, fill_color.Alpha())
        if border_color is not None:
            _controller.set_node_border_rgb(net_index, node_index, border_color)
            _controller.set_node_border_alpha(net_index, node_index, border_color.Alpha())
        if border_width is not None:
            _controller.set_node_border_width(net_index, node_index, border_width)
        if position is not None:
            _controller.move_node(net_index, node_index, position)
        if size is not None:
            _controller.set_node_size(net_index, node_index, size)


def update_reaction(net_index: int, reaction_index: int, id_: str = None,
                    fill_color: wx.Colour = None, thickness: float = None, ratelaw: str = None):
    """
    Update one or multiple properties of a reaction.

    Args:
        net_index: The network index.
        reaction_index: The reaction index of the reaction to modify.
        id_: If specified, the new ID of the reaction.
        fill_color: If specified, the new fill color of the reaction.
        thickness: If specified, the thickness of the reaction.
        ratelaw: If specified, the rate law of the equation.

    Note:
        This is *not* an atomic function, meaning if we failed to set one specific property, the
        previous changes to model in this function will not be undone, even after the exception
        is caught. To go around that, make one calls to update_node() for each property instead.

    Raises:
        ValueError: If ID is empty or if thickness is less than zero.
        NetIndexError:
        ReactionIndexError:
    """
    # TODO get old reaction
    # Validate
    # Check ID not empty
    if id_ is not None and len(id_) == 0:
        raise ValueError('id_ cannot be empty')

    with group_action():
        if id_ is not None:
            _controller.rename_reaction(net_index, reaction_index, id_)
        if fill_color is not None:
            _controller.set_reaction_fill_rgb(net_index, reaction_index, fill_color)
            _controller.set_reaction_fill_alpha(net_index, reaction_index, fill_color.Alpha())
        if thickness is not None:
            _controller.set_reaction_line_thickness(net_index, reaction_index, thickness)
        if ratelaw is not None:
            _controller.set_reaction_ratelaw(net_index, reaction_index, ratelaw)


# def update_node(net_index: int, node_index: int, id_: str = None, fill_color: wx.Colour = None,
#                 border_color: wx.Colour = None, border_width: float = None, position: Vec2 = None,
#                 size: Vec2 = None):
def update_compartment(net_index: int, comp_index: int, id_: str = None,
                       fill_color: wx.Colour = None, border_color: wx.Colour = None,
                       border_width: float = None, volume: float = None,
                       position: Vec2 = None, size: Vec2 = None):
    """
    Update one or multiple properties of a compartment.

    Args:
        net_index: The network index.
        comp_index: The compartment index of the compartment to modify.
        id_: If specified, the new ID of the node.
        fill_color: If specified, the new fill color of the compartment.
        border_color: If specified, the new border color of the compartment.
        border_width: If specified, the new border width of the compartment.
        volume: If specified, the new volume of the compartment.
        position: If specified, the new position of the compartment.
        size: If specified, the new size of the compartment.

    Note:
        This is *not* an atomic function, meaning if we failed to set one specific property, the
        previous changes to model in this function will not be undone, even after the exception
        is caught. To go around that, make one calls to update_node() for each property instead.

    ValueError: If ID is empty or if any one of border_width, position, and size is out of
                range.
    NetIndexError:
    CompartmentIndexError:
    """
    old_comp = get_compartment_by_index(net_index, comp_index)
    # Validate
    #Check ID not empty
    if id_ is not None and len(id_) == 0:
        raise ValueError('id_ cannot be empty')

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
                             'corner exceed canvas boundary {}', pos, sz, _canvas.realsize)

    with group_action():
        if id_ is not None:
            _controller.rename_compartment(net_index, comp_index, id_)
        if fill_color is not None:
            _controller.set_compartment_fill(net_index, comp_index, fill_color)
        if border_color is not None:
            _controller.set_compartment_border(net_index, comp_index, border_color)
        if border_width is not None:
            _controller.set_compartment_border_width(net_index, comp_index, border_width)
        if volume is not None:
            _controller.set_compartment_volume(net_index, comp_index, volume)
        if position is not None:
            _controller.move_compartment(net_index, comp_index, position)
        if size is not None:
            _controller.set_compartment_size(net_index, comp_index, size)


def update_reactant_stoich(net_index: int, reaction_index: int, node_index: int, stoich: int):
    """ 
    Updates the stoichiometry of a reactant node.

    Args:  
        net_index: The network index
        reaction_index: The index of the reaction.
        node_index: The index of the node which must be a reactant of the reaction.
        stoich: The new stoichiometry value.

    """
    _controller.set_src_node_stoich(net_index, reaction_index, node_index, stoich)


def update_product_stoich(net_index: int, reaction_index: int, node_index: int, stoich: int):
    """ 
    Updates the product's stoichiometry.

    Args:  
        net_index: The network index
        reaction_index: The index of the reaction
        node_index: The index of the node which must be a product of the reaction.
        stoich: The new stoichiometry value.
    """
    _controller.set_dest_node_stoich(net_index, reaction_index, node_index, stoich)


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
