# pylint: disable=maybe-no-member
import wx
import sys
import logging
import logging.config
import traceback
from rkviewer.view import RKView
from rkviewer.controller import Controller
import os
from pathlib import Path


class ExceptionDialog(wx.MessageDialog):
    def __init__(self, msg):
        """Constructor"""
        super().__init__(None, msg, "Unknown Exception", wx.OK | wx.ICON_ERROR)


# for monkey-patching exceptions
def create_excepthook(old_excepthook):
    dlg = None
    # whether we've already displayed the dialog once, since wx might take some time to die
    over = False

    def custom_excepthook(etype, value, tb):
        nonlocal over, dlg
        if over:
            return
        over = True
        err_msg = ''.join(traceback.format_exception(etype, value, tb))
        logging.error(err_msg)
        #old_excepthook(etype, value, traceback)
        if dlg is None:
            dlg = ExceptionDialog(err_msg)
            dlg.ShowModal()

            wx.GetApp().GetTopWindow().Destroy()

            dlg.Destroy()
            dlg = None

    return custom_excepthook


def setup_logging():
    d = {
        'version': 1,
        'formatters': {
            'detailed': {
                'class': 'logging.Formatter',
                'format': '%(asctime)s %(name)-15s %(levelname)-8s %(message)s'
            },
            'plugins': {
                'class': 'logging.Formatter',
                'format': '%(asctime)s %(filename)-15s %(levelname)-8s %(message)s',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'stream': 'ext://sys.stdout',
            },
            'debug': {
                'class': 'logging.FileHandler',
                'filename': 'rkviewer.log',
                'mode': 'w',
                'level': 'DEBUG',
                'formatter': 'detailed',
            },
            # 'errors': {
            #     'class': 'logging.FileHandler',
            #     'filename': 'rkviewer-errors.log',
            #     'mode': 'w',
            #     'level': 'ERROR',
            #     'formatter': 'detailed',
            # },
            'plugin-debug': {
                'class': 'logging.FileHandler',
                'filename': 'rkviewer-plugins.log',
                'mode': 'w',
                'level': 'DEBUG',
                'formatter': 'plugins',
            }
        },
        'loggers': {
            'controller': {
                'handlers': ['debug']
            },
            'canvas': {
                'handlers': ['debug']
            },
            'plugin': {
                'handlers': ['plugin-debug']
            },
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['console', 'debug']
        },
    }
    logging.config.dictConfig(d)


if __name__ == '__main__':
    setup_logging()

    # global old_excepthook
    # old_excepthook = sys.excepthook
    sys.excepthook = create_excepthook(sys.excepthook)

    logging.info('Initializing RKViewer...')
    view = RKView()
    controller = Controller(view)
    view.bind_controller(controller)
    view.init()
    view.main_loop()
