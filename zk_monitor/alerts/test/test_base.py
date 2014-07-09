import mock

from tornado.testing import unittest

from zk_monitor.alerts import base


class TestBaseAlerter(unittest.TestCase):
    def setUp(self):
        self.alerter = base.AlerterBase()

    def testAlert(self):
        # Mock up up the AlerterBase self._alert() method because it doesn't
        # actually exist -- its meant to be created by the Alerter that
        # subclasses from the AlerterBase.
        self.alerter._alert = mock.MagicMock()

        # Fire off an alert?
        self.alerter.alert('unittest')

        # Now validate that only one alert was sent
        self.alerter._alert.assert_called_once_with('unittest', params=None)
