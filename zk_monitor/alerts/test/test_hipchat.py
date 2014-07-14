import mock

from tornado.testing import unittest

from zk_monitor.alerts import rest
from zk_monitor.monitor import states


class TestHipchatAlerter(unittest.TestCase):
    def setUp(self):
        self.alerter = rest.HipchatAlerter()

    def test_alert(self):

        fetcher = mock.MagicMock()
        self.alerter._get_client = mock.MagicMock(return_value=fetcher)

        self.alerter.alert('/foo', states.ERROR, 'Site is down.', {
            'room': 'test',
            'token': 'hello :)',
        })

        fetcher.fetch.assert_called_once()

    def test_single_client(self):

        once = self.alerter._get_client()
        twice = self.alerter._get_client()

        self.assertEquals(once, twice)

    def test_request_handled(self):
        request = mock.MagicMock()
        request.error = 'Failed'
        self.assertFalse(self.alerter._handle_request(request))
        request.error = None
        self.assertTrue(self.alerter._handle_request(request))
