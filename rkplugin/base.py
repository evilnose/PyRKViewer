import abc
from .api import Node


class IPlugin(abc.ABC):
    @abc.abstractmethod
    def on_node_added(self, node: Node):
        pass

    @abc.abstractmethod
    def on_node_moved(self, node: Node):
        pass
