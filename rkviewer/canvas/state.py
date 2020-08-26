from dataclasses import dataclass

@dataclass
class CanvasState:
    scale: float = 1

cstate = CanvasState()