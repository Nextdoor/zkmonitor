from tornado import testing

from zk_monitor.web import app


class TestApp(testing.AsyncHTTPTestCase):
    def get_app(self):
        return app.getApplication(None, None, None)

    @testing.gen_test
    def testApp(self):
        """Test that the application starts up and serves basic requests"""
        self.http_client.fetch(self.get_url('/'), self.stop)
        response = self.wait()
        self.assertEquals(200, response.code)
