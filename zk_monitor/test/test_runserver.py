import logging

from tornado.testing import unittest

from zk_monitor import utils
from zk_monitor import runserver


class TestRunserver(unittest.TestCase):
    def testGetRootLogger(self):
        """Test getRootLogger() method"""
        logger = runserver.getRootLogger('iNfO', 'level0')
        self.assertTrue(isinstance(logger, logging.RootLogger))
