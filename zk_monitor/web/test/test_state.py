import mock
import json
from tornado import web
from tornado import testing

from zk_monitor.web import state


class StatusHandlerIntegrationTests(testing.AsyncHTTPTestCase):
    def get_app(self):
        self.mocked_sr = mock.MagicMock()
        self.mocked_monitor = mock.MagicMock()
        self.mocked_monitor.state.return_value = 'test'

        self.settings = {
            'ndsr': self.mocked_sr,
            'monitor': self.mocked_monitor,
        }
        URLS = [(r'/', state.StatusHandler,
                dict(settings=self.settings))]
        return web.Application(URLS)

    @testing.gen_test
    def testState(self):
        """Make sure the returned state information is valid"""
        self.mocked_sr._zk.connected = True
        self.http_client.fetch(self.get_url('/'), self.stop)
        response = self.wait()

        # Load the expected JSON response into a dict
        body_to_dict = json.loads(response.body)

        # Ensure the right keys are in it
        self.assertEquals(True, body_to_dict['zookeeper']['connected'])
        self.assertEquals('test', body_to_dict['monitor'])
        self.assertEquals('0.0.1', body_to_dict['version'])
