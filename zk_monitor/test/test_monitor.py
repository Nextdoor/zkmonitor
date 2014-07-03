import mock

from tornado import testing

from zk_monitor import monitor

import logging

log = logging.getLogger(__name__)


class TestMonitor(testing.AsyncTestCase):
    def setUp(self):
        super(TestMonitor, self).setUp()

        self.mocked_ndsr = mock.MagicMock()
        self.mocked_cs = mock.MagicMock()
        self.paths = {
            '/foo': {'children': 1, 'alerter': {'email': 'unit@test.com'}},
            '/bar': {'children': 2},
            '/baz': None}
        self.monitor = monitor.Monitor(
            self.mocked_ndsr,
            self.mocked_cs,
            self.paths)

        self.monitor._dispatcher = mock.MagicMock()

    def testInit(self):
        self.mocked_ndsr.get_state.assert_called_with(
            self.monitor._stateListener)

    def testStateListener(self):
        test_state = 'test'
        self.monitor._stateListener(test_state)
        self.assertEquals(test_state, self.monitor._state)

    def testValidateConfig(self):
        # Should return right away if the config is empty
        self.assertEquals(None, self.monitor._validateConfig(None))
        self.assertEquals(None, self.monitor._validateConfig([]))

        # Should return properly if we supply an integer as a config setting
        config = {'children': 1}
        self.assertEquals(None, self.monitor._validateConfig(config))

        # Should raise an exception if we pass in an invalid children setting
        config = {'children': 'should fail'}
        self.assertRaises(monitor.InvalidConfigException,
                          self.monitor._validateConfig, config)
        config = {'children': None}
        self.assertRaises(monitor.InvalidConfigException,
                          self.monitor._validateConfig, config)

    def testValidatePaths(self):
        # Should return right away if the config is empty
        self.assertEquals(None, self.monitor._validatePaths(None))
        self.assertEquals(None, self.monitor._validatePaths([]))

        # Should return properly if we supply an integer as a config setting
        config = {
            '/foo': {'children': 1},
            '/bar': {'children': 2},
            '/baz': {}}
        self.assertEquals(None, self.monitor._validatePaths(config))

        # Should raise an exception if we pass in an invalid children setting
        config = {
            '/foo': {'children': 'invalid'},
            '/bar': {'children': 2},
            '/baz': {}}
        self.assertRaises(monitor.InvalidConfigException,
                          self.monitor._validatePaths, config)

    def testWatchPaths(self):
        paths = ['/foo', '/bar']
        self.monitor._watchPaths(paths)
        expected_calls = [
            mock.call('/foo', callback=self.monitor._pathUpdateCallback),
            mock.call('/bar', callback=self.monitor._pathUpdateCallback)
        ]
        self.mocked_ndsr.get.assert_has_calls(expected_calls)

    @testing.gen_test
    def testPathUpdateCallback(self):
        def bar_one_child(path):
            data = {
                '/bar': {'data': None, 'stat': None,
                         'children': ['child1:123']},
            }
            return data[path]
        self.mocked_ndsr.get = bar_one_child
        self.monitor._pathUpdateCallback({'path': '/bar'})
        self.monitor._dispatcher.update.assert_called_with(
            state='Error', data={'path': '/bar'})

    @testing.gen_test
    def testPathUpdateCallbackWithAlerterParams(self):
        def side_effect(path):
            data = {
                '/foo': {'data': None, 'stat': None,
                         'children': []},
            }
            return data[path]
        self.mocked_ndsr.get = side_effect
        self.monitor._pathUpdateCallback({'path': '/foo'})
        self.monitor._dispatcher.update.assert_called_with(
            state='Error', data={'path': '/foo'})

    def testVerifyCompliance(self):
        def side_effect(path):
            data = {
                '/foo': {'data': None, 'stat': None,
                         'children': ['child1:123']},
                '/bar': {'data': None, 'stat': None,
                         'children': ['child1:123']},
                '/baz': {'data': None, 'stat': None, 'children': []}
            }
            return data[path]
        self.mocked_ndsr.get = side_effect

        # /foo is fully compliant
        self.assertEquals(
            (True, 'OK'), self.monitor._get_compliance('/foo'))
        # /bar should have 2 children, but has only 1
        self.assertEquals(
            (False, 'Error'), self.monitor._get_compliance('/bar'))
        # /baz has no children count requirement in the config file.
        self.assertEquals(
            (True, 'Unknown'), self.monitor._get_compliance('/baz'))

    def testDispatchConditions(self):
        self.assertTrue(
            self.monitor._should_update_dispatcher(
                'Unknown', 'Error'))
        self.assertFalse(
            self.monitor._should_update_dispatcher(
                'Unknown', 'OK'))
        self.assertFalse(
            self.monitor._should_update_dispatcher(
                'OK', 'OK'))

    def testState(self):
        def side_effect(path):
            data = {
                '/foo': {'data': None, 'stat': None,
                         'children': ['child1:123']},
                '/bar': {'data': None, 'stat': None,
                         'children': ['child1:123']},
                '/baz': {'data': None, 'stat': None, 'children': []}
            }
            return data[path]
        self.mocked_ndsr.get = side_effect
        ret_val = self.monitor.status()

        self.assertTrue('compliance' in ret_val)
        self.assertEquals('OK', ret_val['compliance']['/foo'])
        self.assertEquals('Error', ret_val['compliance']['/bar'])
        self.assertEquals('Unknown', ret_val['compliance']['/baz'])


# Integration test
class TestWithDispatcher(testing.AsyncTestCase):
    def setUp(self):
        super(TestWithDispatcher, self).setUp()

        self.mocked_ndsr = mock.MagicMock()
        self.mocked_cs = mock.MagicMock()
        self.paths = {
            '/foo': {'children': 1, 'alerter': {'email': 'unit@test.com'}},
            '/bar': {'children': 2},
            '/baz': None}
        self.monitor = monitor.Monitor(
            self.mocked_ndsr,
            self.mocked_cs,
            self.paths)

        # We want to keep the dispatcher real, but not alert anything.
        self.monitor._dispatcher.send_alerts = mock.MagicMock()

    @testing.gen_test
    def test_dispatched_alert(self):
        """Test that monitor causes an actual alert when something is broken.

        Unit tests cover that dispatcher is updated, here we test that the
        integration between Monitor and an actual send_alert() function exists.
        """
        def one_child(path):
            data = {
                '/foo': {'data': None, 'stat': None,
                         'children': []},
            }
            return data[path]
        self.mocked_ndsr.get = one_child
        yield self.monitor._pathUpdateCallback({'path': '/foo'})
        (self.monitor._dispatcher
                     .send_alerts
                     .assert_called_with({'path': '/foo'}))
