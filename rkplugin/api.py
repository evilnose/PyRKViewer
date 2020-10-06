"""
API manager for the rkplugins.

"""

# pylint: disable=maybe-no-member
from iodine import NetIndexNotFoundError
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


def cur_net_index() -> int:
    return _canvas.net_index


@contextmanager
def group_action():
    """Context manager for doing a group operation in the controller, for undo/redo purposes.

    TODO more documentation on this
    """
    _controller.start_group()
    yield
    _controller.end_group()


def all_nodes() -> List[Node]:
    """ 
    Returns the list of all nodes.

    Note:
        Modifying elements of this list will not update the canvas.

    Returns:
        The list of nodes.
    """
    return _controller.get_list_of_nodes(cur_net_index())


def all_reactions() -> List[Reaction]:
    """ 
    Returns the list of all reactions.

    Note:
        Modifying elements of this list will not update the canvas.
    
    Returns:
        The list of reactions.
    """
    return _controller.get_list_of_reactions(cur_net_index())


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


def add_node(net_index: int, node: Node):
    """ 
    Adds a node to the given network.

    The node indices are assigned in increasing order, regardless of deletion.

    Args:  
        net_index: The network index.
        node: The Node to add.
    """
    _controller.add_node_g(net_index, node)


def add_reaction(net_index: int, reaction: Reaction):
    """ 
    Adds a reaction.

    The reaction indices are assigned in increasing order, regardless of deletion.

    Args:  
        net_index: the index overall
        reaction: the Reaction to add
    """
    _controller.add_reaction_g(net_index, reaction)


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

    Raises:
        ValueError: If ID is empty or if at least one of border_width, position, and size is out of
                    range.
    """
    # Make sure this node exists
    old_node = get_node_by_index(net_index, node_index)
    # Validate
    # Check ID not empty
    if id_ is not None and len(id_) == 0:
        raise ValueError('id_ cannot be empty')

    # Check border at least 0
    if border_width is not None and border_width < 0:
        raise ValueError("border_width must be at least 0")

    # Check position at least 0
    if position is not None and (position.x < 0 or position.y < 0):
        raise ValueError("position cannot have negative coordinates, but got '{}'".format(position))

    # Check size at least 0
    if size is not None and (size.x < 0 or size.y < 0):
        raise ValueError("size cannot have negative coordinates, but got '{}'".format(size))

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

    Raises:
        ValueError: If ID is empty, thickness is out of range, or the rate law is set to zero.

    """
    # TODO get old reaction
    # Validate
    # Check ID not empty
    if id_ is not None and len(id_) == 0:
        raise ValueError('id_ cannot be empty')

    if thickness is not None and thickness < 0:
        raise ValueError('thickness must be at least 0')

    if ratelaw is not None and len(ratelaw) == 0:
        raise ValueError('ratelaw cannot be empty')

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

