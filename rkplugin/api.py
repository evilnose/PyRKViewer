# pylint: disable=maybe-no-member
from iodine import NetIndexOutOfRangeError
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
    global _canvas, _controller
    _canvas = canvas
    _controller = controller


def cur_net_index() -> int:
    return _canvas.net_index


@contextmanager
def group_action():
    _controller.start_group()
    yield
    _controller.end_group()


def all_nodes() -> List[Node]:
    return _canvas.nodes


def all_reactions() -> List[Reaction]:
    return _canvas.reactions


def selected_nodes() -> List[Node]:
    return _canvas.GetSelectedNodes()


def selected_node_indices() -> Set[int]:
    return _canvas.sel_nodes_idx.item_copy()


def selected_reaction_indices() -> Set[int]:
    return _canvas.sel_reactions_idx.item_copy()


def get_node_by_index(net_index: int, node_index: int) -> Node:
    pass


def get_reaction_by_index(net_index: int, reaction_index: int) -> Node:
    reactions = [n for n in _canvas.nodes]
    return nodes[0]


# TODO add "cosmetic" versions of these functions, where changes made to controller are not added
# to the history stack. This requires controller to have "programmatic group" feature, i.e. actions
# performed inside such groups are not recorded. programmatic groups nested within group operations
# should be ignored.
def update_node(net_index: int, node_index: int, id_: str = None, fill_color: wx.Colour = None,
                border_color: wx.Colour = None, border_width: float = None, position: Vec2 = None,
                size: Vec2 = None):
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
    if position.x < 0 or position.y < 0:
        raise ValueError("position cannot have negative coordinates, but got '{}'".format(position))

    # Check size at least 0
    if size.x < 0 or size.y < 0:
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


def update_source_stoich(net_index: int, reaction_index: int, node_index: int, stoich: int):
    pass


def get_arrow_tip() -> ArrowTip:
    return cstate.arrow_tip.clone()


def get_default_arrow_tip() -> ArrowTip:
    return ArrowTip(copy.copy(DEFAULT_ARROW_TIP))


def set_arrow_tip(value: ArrowTip):
    cstate.arrow_tip = value.clone()
    _canvas.ArrowTipChanged()
    # TODO save to settings; pending https://github.com/evilnose/PyRKViewer/issues/16
