# pylint: disable=maybe-no-member
import wx
from contextlib import contextmanager
from rkviewer.mvc import IController
from typing import List, Optional, Set
from rkviewer.controller import Controller
from rkviewer.canvas.canvas import Canvas
from rkviewer.canvas import data
from rkviewer.canvas.state import cstate

Node = data.Node
Reaction = data.Reaction

# TODO allow modification of theme and setting

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
    _controller.try_start_group()
    yield
    _controller.try_end_group()


def all_nodes() -> List[Node]:
    return _canvas.nodes


def all_reactions() -> List[Reaction]:
    return _canvas.reactions


def selected_nodes() -> List[Node]:
    # TODO copy?
    return _canvas.GetSelectedNodes()


def selected_node_indices() -> Set[int]:
    return _canvas.selected_idx.item_copy()


def selected_reaction_indices() -> Set[int]:
    return _canvas.sel_reactions_idx.item_copy()


def get_node_by_index(index: int) -> Node:
    nodes = [n for n in _canvas.nodes]
    assert len(nodes) <= 1
    return nodes[0]


# TODO add "cosmetic" versions of these functions, where changes made to controller are not added
# to the history stack. This requires controller to have "programmatic group" feature, i.e. actions
# performed inside such groups are not recorded. programmatic groups nested within group operations
# should be ignored.
def set_node_fill(net_idx: int, node_idx: int, color: wx.Colour):
    _controller.try_start_group()
    _controller.try_set_node_fill_rgb(net_idx, node_idx, color)
    _controller.try_set_node_fill_alpha(net_idx, node_idx, color.Alpha())
    _controller.try_end_group()


def set_node_border(net_idx: int, node_idx: int, color: wx.Colour):
    _controller.try_start_group()
    _controller.try_set_node_border_rgb(net_idx, node_idx, color)
    _controller.try_set_node_border_alpha(net_idx, node_idx, color.Alpha())
    _controller.try_end_group()

def set_reaction_fill(net_idx: int, rxn_idx: int, color: wx.Colour):
    _controller.try_start_group()
    _controller.try_set_reaction_fill_rgb(net_idx, rxn_idx, color)
    _controller.try_set_reaction_fill_alpha(net_idx, rxn_idx, color.Alpha())
    _controller.try_end_group()
