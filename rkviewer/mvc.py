# pylint: disable=maybe-no-member
import wx
import abc
from typing import List
from .utils import Vec2, Node


class IController(abc.ABC):
    """The inteface class for a controller

    The abc.ABC (Abstract Base Class) is used to enforce the MVC interface more
    strictly.

    The methods with name beginning with Try- are usually called by the View after
    some user input. If the action tried in such a method succeeds, the Controller
    should request the view to be redrawn; otherwise, an error message might be shown.
    """

    @abc.abstractmethod
    def try_start_group(self) -> bool:
        """Try to signal start of group operation"""
        pass

    @abc.abstractmethod
    def try_end_group(self) -> bool:
        """Try to signal end of group operation"""
        pass

    @abc.abstractmethod
    def try_undo(self) -> bool:
        """Try to undo last operation"""
        pass

    @abc.abstractmethod
    def try_redo(self) -> bool:
        """Try to redo last undone operation"""
        pass

    @abc.abstractmethod
    def try_add_node(self, node: Node) -> bool:
        """Try to add the given Node to the canvas."""
        pass

    @abc.abstractmethod
    def try_move_node(self, id_: str, pos: Vec2) -> bool:
        """Try to move the give node. TODO only accept node ID and new location"""
        pass

    @abc.abstractmethod
    def try_set_node_size(self, id_: str, size: Vec2) -> bool:
        """Try to move the give node. TODO only accept node ID and new location"""
        pass

    @abc.abstractmethod
    def try_rename_node(self, old_id: str, new_id: str) -> bool:
        pass

    @abc.abstractmethod
    def try_set_node_fill_rgb(self, id_: str, color: wx.Colour) -> bool:
        pass

    @abc.abstractmethod
    def try_set_node_fill_alpha(self, id_: str, alpha: float) -> bool:
        pass

    @abc.abstractmethod
    def try_set_node_border_rgb(self, id_: str, color: wx.Colour) -> bool:
        pass

    @abc.abstractmethod
    def try_set_node_border_alpha(self, id_: str, alpha: float) -> bool:
        pass

    @abc.abstractmethod
    def try_set_node_border_width(self, id_: str, width: float) -> bool:
        pass

    @abc.abstractmethod
    def try_delete_node(self, id_: str) -> bool:
        pass

    @abc.abstractmethod
    def get_list_of_node_ids(self) -> List[str]:
        """Try getting the list of node IDs"""
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
    def update_all(self, nodes):
        """Update all the graph objects, and redraw everything at the end"""
        pass
