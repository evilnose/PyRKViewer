# pylint: disable=maybe-no-member
from typing import List
from rkviewer.canvas.geometry import Vec2
from rkviewer.canvas.data import Compartment, Node, Reaction
from rkplugin import api
from rkviewer.controller import Controller
import wx
from contextlib import contextmanager
import threading
from rkviewer.view import View

@contextmanager
def run_app():
    """Create an app context. The app main loop is not called."""
    view = View()
    controller = Controller(view)
    view.bind_controller(controller)
    view.init()
    app = wx.App()
    yield app
    app.Destroy()
    api.uninit_api()

def open_app_context(context):
    context.__enter__()

def close_app_context(context):
    context.__exit__(None, None, None)

# convenience functions that create a Node/Reaction/Compartment with arbitrary properties.
def auto_node(id_: str, neti: int) -> Node:
    return Node(id_,
                neti,
                pos=Vec2(550, 450),
                size=Vec2(50, 30),
                fill_color=wx.RED,
                border_color=wx.GREEN,
                border_width=2)

def auto_reaction(id_: str, neti: int, sources: List[int], targets: List[int]) -> Reaction:
    return Reaction(
        id_=id_,
        net_index=neti,
        sources=sources,
        targets=targets,
        handle_positions=[Vec2() for _ in range(len(sources) + len(targets) + 1)],
        fill_color=wx.RED,
        line_thickness=2,
        rate_law=''
    )

def auto_compartment(id_: str, neti: int) -> Compartment:
    return Compartment(
        id_=id_,
        net_index=neti,
        nodes=list(),
        position=Vec2(400, 400),
        size=Vec2(200, 200),
        fill=wx.BLUE,
        border=wx.GREEN,
        border_width=2,
        volume=1,
    )