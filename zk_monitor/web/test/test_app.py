import socket

from tornado import testing
import mock

from zk_monitor.web import app

all_sockets = socket.getaddrinfo(
    'localhost', 0, socket.AF_INET, socket.SOCK_STREAM)

if len(all_sockets) > 1:
    socket.getaddrinfo = mock.Mock(return_value=[all_sockets[0]])


class TestApp(testing.AsyncHTTPTestCase):

    def get_app(self):
        run = app.getApplication(None, None, None)
        return run

    def testApp(self):
        """Test that the application starts up and serves basic requests"""
        self.http_client.fetch(self.get_url('/'), self.stop)
        response = self.wait()
        self.assertEquals(200, response.code)
