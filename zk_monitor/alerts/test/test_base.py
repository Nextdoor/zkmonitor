import mock

from tornado.testing import unittest

from zk_monitor.alerts import base


class TestBaseAlerter(unittest.TestCase):
    def setUp(self):
        self.mocked_ndsr = mock.MagicMock()
        self.mocked_lock = mock.MagicMock()
        self.mocked_ndsr.get_lock.return_value = self.mocked_lock
        self.lock_path = '/lock_test'
        self.alerter = base.AlerterBase(self.mocked_ndsr, self.lock_path)

    def testBeginLock(self):
        self.mocked_ndsr.get_lock.assert_called_with(self.lock_path, wait=0)
        self.mocked_lock.acquire.assert_called()

    def testStatus(self):
        self.assertTrue('alerting' in self.alerter.status())
