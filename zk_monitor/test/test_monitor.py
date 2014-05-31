import mock
import logging

from tornado.testing import unittest

from zk_monitor import monitor


class TestMonitor(unittest.TestCase):
    def setUp(self):
        self.ndsr = mock.MagicMock()
        self.paths = {
          '/foo': { 'children': 1 },
          '/bar': { 'children': 2 },
          '/baz': None }
        self.monitor = monitor.Monitor(self.ndsr, self.paths)

    def testInit(self):
        self.ndsr.get_state.assert_called_with(self.monitor._stateListener)

    def testStateListener(self):
        test_state = 'test'
        self.monitor._stateListener(test_state)
        self.assertEquals(test_state, self.monitor._state)

    def testValidateConfig(self):
        # Should return right away if the config is empty
        self.assertEquals(None, self.monitor._validateConfig(None))
        self.assertEquals(None, self.monitor._validateConfig([]))

        # Should return properly if we supply an integer as a config setting
        config = { 'children': 1 }
        self.assertEquals(None, self.monitor._validateConfig(config))

        # Should raise an exception if we pass in an invalid children setting
        config = { 'children': 'should fail' }
        self.assertRaises(monitor.InvalidConfigException,
                          self.monitor._validateConfig, config)
        config = { 'children': None }
        self.assertRaises(monitor.InvalidConfigException,
                          self.monitor._validateConfig, config)


    def testValidatePaths(self):
        # Should return right away if the config is empty
        self.assertEquals(None, self.monitor._validatePaths(None))
        self.assertEquals(None, self.monitor._validatePaths([]))

        # Should return properly if we supply an integer as a config setting
        config = {
          '/foo': { 'children': 1 },
          '/bar': { 'children': 2 },
          '/baz': { } }
        self.assertEquals(None, self.monitor._validatePaths(config))

        # Should raise an exception if we pass in an invalid children setting
        config = {
          '/foo': { 'children': 'invalid' },
          '/bar': { 'children': 2 },
          '/baz': { } }
        self.assertRaises(monitor.InvalidConfigException,
                          self.monitor._validatePaths, config)

    def testWatchPaths(self):
        paths = [ '/foo', '/bar' ]
        self.monitor._watchPaths(paths)
        expected_calls = [mock.call('/foo'), mock.call('/bar')]
        self.ndsr.get.assert_has_calls(expected_calls)

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
        self.ndsr.get = side_effect

        self.assertEquals(True, self.monitor._verifyCompliance('/foo'))
        self.assertNotEquals(True, self.monitor._verifyCompliance('/bar'))
        self.assertEquals(True, self.monitor._verifyCompliance('/baz'))

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
        self.ndsr.get = side_effect
        ret_val = self.monitor.state()

        self.assertTrue('compliance' in ret_val)
        self.assertEquals(True, ret_val['compliance']['/foo'])
        self.assertEquals('Found children (1) less than minimum (2)',
                ret_val['compliance']['/bar'])
        self.assertEquals(True, ret_val['compliance']['/baz'])
