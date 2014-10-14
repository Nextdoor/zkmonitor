from tornado import web
from tornado import testing

from zk_monitor.web import root
from zk_monitor.version import __version__ as VERSION


class RootHandlerIntegrationTests(testing.AsyncHTTPTestCase):
    def get_app(self):
        return web.Application([('/', root.RootHandler)])

    def testIndexIncludesVersion(self):
        """Make sure the version number was presented properly"""
        self.http_client.fetch(self.get_url('/'), self.stop)
        response = self.wait()
        self.assertIn(VERSION, response.body)
