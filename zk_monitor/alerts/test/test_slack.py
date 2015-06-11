"""Tests for the actors.slack package"""

import mock

from tornado import testing
from tornado_rest_client import exceptions
from tornado_rest_client.clients import slack

from zk_monitor.test import helper
from zk_monitor.alerts import slack as slack_alert
from zk_monitor.monitor import states


__author__ = 'Matt Wise <matt@nextdoor.com>'


class TestSlackAlerter(testing.AsyncTestCase):

    """Unit tests for the SlackAlerter."""

    def test_style_from_state(self):
        alerter = slack_alert.SlackAlerter()

        ok = alerter.style_from_state(states.OK)
        error = alerter.style_from_state(states.ERROR)
        grey = alerter.style_from_state('bogus')

        self.assertEquals(ok, ':+1:')
        self.assertEquals(error, ':exclamation:')
        self.assertEquals(grey, ':grey_question:')

    @testing.gen_test
    def test_alert(self):
        alerter = slack_alert.SlackAlerter()

        params = {
            'channel': '#oncall',
            'from': 'ZK Monitor Test',
            'token': 'unittest'
        }

        post_message_mock = mock.MagicMock(name='chat_postMessage')
        post_message_mock.http_post = helper.mock_tornado(value='test')

        slack_mock = mock.MagicMock(name='SlackAPI')
        slack_mock.chat_postMessage.side_effect = post_message_mock

        with mock.patch.object(slack, 'Slack') as slack_mock:
            # Mock out the chat_postMessage().http_post() method
            m = helper.mock_tornado('test_value')
            slack_mock().chat_postMessage().http_post = m

            ret = yield alerter._alert('/test', states.OK, 'Happy', params)

        self.assertEquals(ret, slack_mock().check_results())
        self.assertEquals(
            slack_mock().chat_postMessage().http_post._call_count, 1)

    @testing.gen_test
    def test_alert_raises_exc(self):
        alerter = slack_alert.SlackAlerter()

        params = {
            'channel': '#oncall',
            'from': 'ZK Monitor Test',
            'token': 'unittest'
        }

        post_message_mock = mock.MagicMock(name='chat_postMessage')
        post_message_mock.http_post = helper.mock_tornado(value='test')

        slack_mock = mock.MagicMock(name='SlackAPI')
        slack_mock.chat_postMessage.side_effect = post_message_mock

        with mock.patch.object(slack, 'Slack') as slack_mock:
            # Mock out the chat_postMessage().http_post() method
            exc = exceptions.InvalidCredentials('Boom')
            slack_mock().chat_postMessage().http_post.side_effect = exc
            ret = yield alerter._alert('/test', states.OK, 'Happy', params)
        self.assertEquals(ret, None)
