# pylint: disable=maybe-no-member
import wx
import abc
from typing import List, Optional
from .canvas.geometry import Vec2
from .canvas.data import Node, Reaction


class IController(abc.ABC):
    """The inteface class for a controller

    The abc.ABC (Abstract Base Class) is used to enforce the MVC interface more
    strictly.

    The methods with name beginning with Try- are usually called by the View after
    some user input. If the action tried in such a method succeeds, the Controller
    should request the view to be redrawn; otherwise, an error message might be shown.
    """

    @abc.abstractmethod
    def start_group(self) -> bool:
        """Try to signal start of group operation"""
        pass

    @abc.abstractmethod
    def end_group(self) -> bool:
        """Try to signal end of group operation"""
        pass

    @abc.abstractmethod
    def in_group(self) -> bool:
        """Returns whether the controller is in the middle of a group operation."""
        pass

    @abc.abstractmethod
    def undo(self) -> bool:
        """Try to undo last operation"""
        pass

    @abc.abstractmethod
    def redo(self) -> bool:
        """Try to redo last undone operation"""
        pass

    @abc.abstractmethod
    def add_node_g(self, neti: int, node: Node) -> bool:
        """Try to add the given Node to the canvas."""
        pass

    @abc.abstractmethod
    def move_node(self, neti: int, nodei: int, pos: Vec2, programmatic: bool = False) -> bool:
        """Try to move the give node. TODO only accept node ID and new location"""
        pass

    @abc.abstractmethod
    def set_node_size(self, neti: int, nodei: int, size: Vec2, programmatic: bool = False) -> bool:
        """Try to move the give node. TODO only accept node ID and new location"""
        pass

    @abc.abstractmethod
    def rename_node(self, neti: int, nodei: int, new_id: str) -> bool:
        pass

    @abc.abstractmethod
    def set_node_fill_rgb(self, neti: int, nodei: int, color: wx.Colour) -> bool:
        pass

    @abc.abstractmethod
    def set_node_fill_alpha(self, neti: int, nodei: int, alpha: int) -> bool:
        pass

    @abc.abstractmethod
    def set_node_border_rgb(self, neti: int, nodei: int, color: wx.Colour) -> bool:
        pass

    @abc.abstractmethod
    def set_node_border_alpha(self, neti: int, nodei: int, alpha: int) -> bool:
        pass

    @abc.abstractmethod
    def set_node_border_width(self, neti: int, nodei: int, width: float) -> bool:
        pass

    @abc.abstractmethod
    def rename_reaction(self, neti: int, reai: int, new_id: str) -> bool:
        pass

    @abc.abstractmethod
    def set_reaction_line_thickness(self, neti: int, reai: int, thickness: float) -> bool:
        pass

    @abc.abstractmethod
    def set_reaction_fill_rgb(self, neti: int, reai: int, color: wx.Colour) -> bool:
        pass

    @abc.abstractmethod
    def set_reaction_fill_alpha(self, neti: int, reai: int, alpha: int) -> bool:
        pass

    @abc.abstractmethod
    def set_reaction_ratelaw(self, neti: int, reai: int, ratelaw: str) -> bool:
        pass

    @abc.abstractmethod
    def delete_node(self, neti: int, nodei: int) -> bool:
        pass

    @abc.abstractmethod
    def delete_reaction(self, neti: int, reai: int) -> bool:
        pass

    @abc.abstractmethod
    def set_src_node_stoich(self, neti: int, reai: int, node_id: str, stoich: float) -> bool:
        pass

    @abc.abstractmethod
    def set_dest_node_stoich(self, neti: int, reai: int, node_id: str, stoich: float) -> bool:
        pass

    @abc.abstractmethod
    def get_src_node_stoich(self, neti: int, reai: int, node_id: str) -> float:
        pass

    @abc.abstractmethod
    def set_src_node_handle(self, neti: int, reai: int, node_id: str, pos: Vec2):
        pass

    @abc.abstractmethod
    def set_dest_node_handle(self, neti: int, reai: int, node_id: str, pos: Vec2):
        pass

    @abc.abstractmethod
    def set_center_handle(self, neti: int, reai: int, pos: Vec2):
        pass

    @abc.abstractmethod
    def get_src_node_handle(self, neti: int, reai: int, node_id: str) -> Vec2:
        pass

    @abc.abstractmethod
    def get_dest_node_handle(self, neti: int, reai: int, node_id: str) -> Vec2:
        pass

    @abc.abstractmethod
    def get_center_handle(self, neti: int, reai: int) -> Vec2:
        pass

    @abc.abstractmethod
    def get_dest_node_stoich(self, neti: int, reai: int, node_id: str) -> float:
        pass

    @abc.abstractmethod
    def get_list_of_src_ids(self, neti: int, reai: int) -> List[str]:
        pass

    @abc.abstractmethod
    def get_list_of_dest_ids(self, neti: int, reai: int) -> List[str]:
        pass

    @abc.abstractmethod
    def get_list_of_node_ids(self, neti: int) -> List[str]:
        """Try getting the list of node IDs"""
        pass

    @abc.abstractmethod
    def get_node_index(self, neti: int, node_id: str) -> int:
        pass

    @abc.abstractmethod
    def get_reaction_index(self, neti: int, rxn_id: str) -> int:
        pass

    @abc.abstractmethod
    def add_reaction_g(self, neti: int, reaction: Reaction) -> bool:
        pass

    @abc.abstractmethod
    def get_node_by_index(self, neti: int, nodei: int) -> Node:
        pass

    @abc.abstractmethod
    def get_reaction_by_index(self, neti: int, reai: int) -> Node:
        pass


class IView(abc.ABC):
    """The inteface class for a controller

    The abc.ABC (Abstract Base Class) is used to enforce the MVC interface more
    strictly.
    """

    @abc.abstractmethod
    def bind_controller(self, controller: IController):
        """Bind the controller. This needs to be called after a controller is 
        created and before any other method is called.
        """
        pass

    @abc.abstractmethod
    def main_loop(self):
        """Run the main loop. This is blocking right now. This may be modified to
        become non-blocking in the future if required.
        """
        pass

    @abc.abstractmethod
    def update_all(self, nodes, reactions):
        """Update all the graph objects, and redraw everything at the end"""
        pass
