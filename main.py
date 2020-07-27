from rkviewer.view import View
from rkviewer.controller import Controller


if __name__ == '__main__':
    view = View()
    controller = Controller(view)
    view.BindController(controller)
    view.MainLoop()
