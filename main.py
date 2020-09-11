# pylint: disable=maybe-no-member
import wx
import sys
import logging
import logging.config
import traceback
from rkviewer.view import View
from rkviewer.controller import Controller


class ExceptionDialog(wx.MessageDialog):
    def __init__(self, msg):
        """Constructor"""
        super().__init__(None, msg, "Unknown Exception", wx.OK|wx.ICON_ERROR)  


# for monkey-patching exceptions
def create_excepthook(old_excepthook):
    dlg = None
    def custom_excepthook(etype, value, tb):
        nonlocal dlg
        err_msg = ''.join(traceback.format_exception(etype, value, tb))
        logging.error(err_msg)
        old_excepthook(etype, value, traceback)

        if dlg is None:
            dlg = ExceptionDialog(err_msg)
            dlg.ShowModal()
            wx.GetApp().GetTopWindow().Destroy()
            dlg.Destroy() 
            dlg = None

    return custom_excepthook


def setup_logging():
    # TODO change level based on whether the app has been packaged
    d = {
        'version': 1,
        'formatters': {
            'detailed': {
                'class': 'logging.Formatter',
                'format': '%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
            },
            'debug': {
                'class': 'logging.FileHandler',
                'filename': 'rkviewer-debug.log',
                'mode': 'w',
                'level': 'DEBUG',
                'formatter': 'detailed',
            },
            'errors': {
                'class': 'logging.FileHandler',
                'filename': 'rkviewer-errors.log',
                'mode': 'w',
                'level': 'ERROR',
                'formatter': 'detailed',
            },
        },
        'loggers': {  # TODO add more loggers here
            'controller': {
                'handlers': ['debug', 'errors']
            }
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['console', 'debug', 'errors']
        },
    }
    logging.config.dictConfig(d)


if __name__ == '__main__':
    setup_logging()

    global old_excepthook
    old_excepthook = sys.excepthook
    sys.excepthook = create_excepthook(sys.excepthook)

    logging.info('Initializing RKViewer...')
    view = View()
    controller = Controller(view)
    view.bind_controller(controller)
    view.main_loop()
