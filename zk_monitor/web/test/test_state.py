import mock
from tornado import web
from tornado import testing

from zk_monitor.web import state
from zk_monitor.version import __version__ as VERSION


class StatusHandlerIntegrationTests(testing.AsyncHTTPTestCase):
    def get_app(self):
        self.mocked_sr = mock.MagicMock()
        self.mocked_paths = {
          '/should_have_1': [ { 'children': 1 } ],
          '/should_have_2': [ { 'children': 2 } ],
          '/should_have_0': [ { 'children': 0 } ],
        }
        self.settings = {
            'ndsr': self.mocked_sr,
            'paths': self.mocked_paths,
        }
        URLS = [(r'/', state.StatusHandler,
                dict(settings=self.settings))]
        return web.Application(URLS)

    @testing.gen_test
    def testIndexIncludesVersion(self):
        """Make sure the version number was presented properly"""
        self.mocked_sr._zk.connected = True
        self.http_client.fetch(self.get_url('/'), self.stop)
        response = self.wait()
        self.assertIn('True', response.body)
