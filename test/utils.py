# pylint: disable=maybe-no-member
from rkviewer.controller import Controller
import wx
from contextlib import contextmanager
import threading
from rkviewer.view import View

@contextmanager
def run_app():
    view = View()
    controller = Controller(view)
    view.bind_controller(controller)
    view.init()
    app = wx.App()
    yield app
    