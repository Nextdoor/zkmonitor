import mock

from tornado.testing import unittest

from zk_monitor import cluster


class TestState(unittest.TestCase):
    @mock.patch('platform.node')
    @mock.patch('os.getpid')
    def setUp(self, getpid_mock, node_mock):
        node_mock.return_value = 'unittest'
        getpid_mock.return_value = 123

        self.mocked_ndsr = mock.MagicMock()
        self.path = '/unittest'

        self.state = cluster.State(self.mocked_ndsr, self.path)

    def testInit(self):
        self.state._path = '/unittest'
        self.assertEquals(self.state._name, 'unittest-123')

    def testGetLock(self):
        self.mocked_ndsr.get_lock.return_value = "fake_lock"
        self.assertEquals("fake_lock", self.state.getLock('unittest'))
        self.mocked_ndsr.get_lock.assert_called_with(
            '/unittest/locks/unittest', 'unittest-123', wait=0)
