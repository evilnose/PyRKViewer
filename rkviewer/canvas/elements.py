from abc import abstractmethod
from .geometry import Vec2

class CanvasElement:
    @abstractmethod
    def pos_inside(self, logical_pos: Vec2, ) -> bool:
        pass
