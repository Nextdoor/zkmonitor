from StringIO import StringIO
import mock
import logging

from tornado.testing import unittest

from zk_monitor import utils
from zk_monitor import runserver


class TestRunserver(unittest.TestCase):
    def testGetRootLogger(self):
        """Test getRootLogger() method"""
        logger = runserver.getRootLogger('iNfO', 'level0')
        self.assertTrue(isinstance(logger, logging.RootLogger))

    def testGetPathListWithValidYAML(self):
        """Test getPathList() method"""
        with mock.patch('__builtin__.open') as m:
            text = "/foo:\n  - children: 1"
            expected_dict = {'/foo': [{'children': 1}]}
            m.return_value = StringIO(text)
            self.assertEquals(expected_dict, runserver.getPathList('/test'))

    def testGetPathListWithInvalidYAML(self):
        """Test getPathList() method with invalid YAML"""
        with mock.patch('__builtin__.open') as m:
            text = "/foo: \nbar"
            m.return_value = StringIO(text)
            self.assertEquals({}, runserver.getPathList('/test'))

    def testGetPathListWithInvalidFile(self):
        """Test getPathList() method with invalid File Path"""
        self.assertEquals({}, runserver.getPathList('/fake_path'))

    def testGetPathListWithNoneFile(self):
        """Test getPathList() method with default path of None"""
        self.assertEquals({}, runserver.getPathList(None))

    def testGetServiceRegistry(self):
        """Test getServiceRegistry() method"""
        with mock.patch('nd_service_registry.KazooServiceRegistry') as m:
            fake_ndsr_object = mock.MagicMock()
            m.return_value = fake_ndsr_object
            self.assertEquals(fake_ndsr_object,
                              runserver.getServiceRegistry('unittest:123'))
            m.assert_called_once_with(lazy=True,
                                      readonly=True,
                                      timeout=1,
                                      server='unittest:123')
