
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
    def try_add_node(self, node: Node) -> bool:
        """Try to add the given Node to the canvas."""
        pass

    @abc.abstractmethod
    def try_move_node(self, id_: str, pos: Vec2):
        """Try to move the give node. TODO only accept node ID and new location"""
        pass

    @abc.abstractmethod
    def try_set_node_size(self, id_: str, size: Vec2):
        """Try to move the give node. TODO only accept node ID and new location"""
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
