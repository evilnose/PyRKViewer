from rkviewer.canvas.elements import CanvasElement as CanvasElement_
from .api import get_canvas
from rkviewer.canvas.utils import draw_rect

CanvasElement = CanvasElement_


def add_element(net_index: int, element: CanvasElement):
    """Add a CanvasElement to the canvas"""
    get_canvas().AddPluginElement(net_index, element)


def remove_element(net_index: int, element: CanvasElement):
    """Remove a CanvasElement from the canvas"""
    get_canvas().RemovePluginElement(net_index, element)
