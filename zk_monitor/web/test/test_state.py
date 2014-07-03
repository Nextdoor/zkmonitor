import mock
import json
from tornado import web
from tornado import testing

from zk_monitor.web import state
from zk_monitor import version
from zk_monitor import monitor


class StatusHandlerIntegrationTests(testing.AsyncHTTPTestCase):
    def get_app(self):
        self.mocked_ndsr = mock.MagicMock(name='ND Serv. Reg')

        self.mocked_cs = mock.MagicMock(name='Cluster State')
        self.mocked_cs.getLock.return_value = mock.MagicMock(name='CS_getLock')
        self.mocked_cs.getLock.return_value.status = mock.MagicMock(
            return_value='cs_getlock_test')

        self.paths = {
            '/foo': 'config',
            '/bar': 'config'}

        self.monitor = monitor.Monitor(
            self.mocked_ndsr,
            self.mocked_cs,
            self.paths)

        self.dispatcher = self.monitor._dispatcher

        self.settings = {
            'ndsr': self.mocked_ndsr,
            'monitor': self.monitor,
            'dispatcher': self.dispatcher,
        }
        URLS = [(r'/', state.StatusHandler,
                dict(settings=self.settings))]
        return web.Application(URLS)

    @testing.gen_test
    def testState(self):
        """Make sure the returned state information is valid"""
        self.mocked_ndsr._zk.connected = True
        self.http_client.fetch(self.get_url('/'), self.stop)
        response = self.wait()

        self.assertTrue('text/json' in response.headers['Content-Type'],
                        'For easier access via standard browsers, the content '
                        'type should be set to text/json so that the browsers '
                        'render it cleanly.')

        # Load the expected JSON response into a dict
        body_to_dict = json.loads(response.body)

        # Ensure the right keys are in it
        self.assertEquals(True, body_to_dict['zookeeper']['connected'])
        self.assertEquals(version.__version__, body_to_dict['version'])

        self.assertTrue('compliance' in body_to_dict['monitor'])

        # Check that compliance is unknown for all paths since we never
        # invoked any updating.
        self.assertEquals({
            'compliance': {
                '/foo': 'Unknown',
                '/bar': 'Unknown'}}, body_to_dict['monitor'])
