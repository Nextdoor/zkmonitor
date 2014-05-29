from tornado import testing
import mock

from zk_monitor import runserver
from zk_monitor import utils
from zk_monitor.web import app


class TestApp(testing.AsyncHTTPTestCase):
    def get_app(self):
        # Generate a real application server based on our test config data
        self.mocked_sr = mock.MagicMock()
        self.mocked_paths = {
          '/should_have_1': [ { 'children': 1 } ],
          '/should_have_2': [ { 'children': 2 } ],
          '/should_have_0': [ { 'children': 0 } ],
        }
        server = app.getApplication(self.mocked_sr, self.mocked_paths)
        return server

    @testing.gen_test
    def testApp(self):
        """Test that the application starts up and serves basic requests"""
        self.http_client.fetch(self.get_url('/'), self.stop)
        response = self.wait()
        self.assertEquals(200, response.code)
