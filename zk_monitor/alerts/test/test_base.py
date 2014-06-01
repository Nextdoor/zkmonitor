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

    def testAlert(self):
        # Mock up up the AlerterBase self._alert() method because it doesn't
        # actually exist -- its meant to be created by the Alerter that
        # subclasses from the AlerterBase.
        self.alerter._alert = mock.MagicMock()

        # Disable our alerting
        self.mocked_lock.status.return_value = False

        # Fire an alert -- it shouldn't do anything
        self.alerter.alert('unittest-disabled')

        # Set our alertering status to True
        self.mocked_lock.status.return_value = True

        # Fire off an alert?
        self.alerter.alert('unittest')

        # Now validate that only one alert was sent
        self.alerter._alert.assert_called_once_with('unittest')
