import unittest
from rkviewer.plugin import api
from rkviewer.config import runtime_vars, reset_runtime_vars
from test.utils import close_app_context, open_app_context, run_app


class DummyAppTest(unittest.TestCase):
    '''Test superclass for functions that need the app, canvas, and controller to be initialized,
    but don't require the windows to be created or the app to be actually running.
    '''
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.neti = 0

    def tearDown(self):
        api.clear_network(self.neti)

    @classmethod
    def setUpClass(cls):
        runtime_vars().enable_plugins = False
        cls.app_handle = None
        cls.app_handle = run_app()
        open_app_context(cls.app_handle)

    @classmethod
    def tearDownClass(cls):
        close_app_context(cls.app_handle)
        reset_runtime_vars()