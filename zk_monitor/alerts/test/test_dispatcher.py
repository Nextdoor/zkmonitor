from tornado import testing
import mock

from zk_monitor import alerts

import logging

log = logging.getLogger(__name__)


class TestDispatcher(testing.AsyncTestCase):
    def setUp(self):
        super(TestDispatcher, self).setUp()

        self.config = {'/bar': {'children': 1,
                                'cancel_timeout': 0.25,
                                'alerter': {'email': 'unit@test.com',
                                            'body': 'unit test body',
                                            'custom': 'something custom'}}}

        self._cs = mock.MagicMock()

    @testing.gen_test
    def test_dispatch_without_timeout(self):
        config_no_timeout = self.config
        config_no_timeout['/bar']['cancel_timeout'] = None

        self.dispatcher = alerts.Dispatcher(self._cs, config_no_timeout)
        self.dispatcher.send_alerts = mock.MagicMock()
        data = {'path': '/bar'}

        # == First dispatch update with an error message - this one will wait
        # for 2 seconds.
        update_task = self.dispatcher.update(data=data, state='Error')

        # == Now simulate OK scenario which will cancel the alert.
        self.dispatcher.update(data=data, state='OK')

        # For the purpose of a unit test - wait for the first callback to
        # finish
        yield update_task

        # Make sure we did NOT fire an alert.
        self.assertTrue(self.dispatcher.send_alerts.called, (
            "Alert should have been fired off before being canceled.\nThis"
            "test relies on the fact that two consequent coroutines\nexecute"
            "consequently."))

    @testing.gen_test
    def test_dispatch_with_cancellation(self):
        self.dispatcher = alerts.Dispatcher(self._cs, self.config)
        self.dispatcher.send_alerts = mock.MagicMock()
        data = {'path': '/bar'}

        # == First dispatch update with an error message - this one will wait
        # for `cancel_timeout` seconds.
        update_task = self.dispatcher.update(data=data, state='Error')

        # == Now simulate OK scenario which will cancel the alert.
        self.dispatcher.update(data=data, state='OK')

        # For the purpose of a unit test - wait for the first callback to
        # finish
        yield update_task

        # Make sure we did NOT fire an alert.
        self.assertFalse(self.dispatcher.send_alerts.called,
                         "Alert should have been canceled.")

    @testing.gen_test
    def test_dispatch_with_alert(self):
        self.dispatcher = alerts.Dispatcher(self._cs, self.config)
        self.dispatcher.send_alerts = mock.MagicMock()
        data = {'path': '/bar'}

        # == First dispatch update with an error message - this one will wait
        # for 2 seconds.
        update_task = self.dispatcher.update(data=data, state='Error')

        # For the purpose of a unit test - wait for the first callback to
        # finish
        yield update_task

        self.dispatcher.send_alerts.assert_called_with(data)

    def test_send_alerts(self):
        # Prepare for testing.
        # '/bar' is configued to use 'email' in self.config
        data = {'path': '/bar'}
        self.dispatcher = alerts.Dispatcher(self._cs, self.config)
        self.dispatcher.alerts['email'] = mock.MagicMock()
        self.dispatcher.alerts['custom'] = mock.MagicMock()

        # Set data, and send the alert
        self.dispatcher.set_status(data, message='unittest')
        self.dispatcher.send_alerts(data)

        # Dispatcher should loop through everything that is under "alerter"
        # setting.  alert call is hardcoded to assume email only for now.
        email_params = {'body': 'unit test body', 'email': 'unit@test.com'}
        # Email...
        self.dispatcher.alerts['email'].alert.assert_called_with(
            message='unittest',
            params=email_params)
        # Testing for custom alerts not real until all alerts are standardized.
        self.dispatcher.alerts['custom'].alert.assert_called_with(
            message='unittest',
            params=email_params)

    def test_status(self):
        """Dispatcher's status should report on all alerts that it uses."""

        self.dispatcher = alerts.Dispatcher(self._cs, self.config)
        self.dispatcher.alerts = {}
        self.dispatcher.alerts['email'] = mock.MagicMock()
        self.dispatcher.alerts['email'].status = mock.Mock(return_value='test')
        self.dispatcher.alerts['other'] = mock.MagicMock()
        self.dispatcher.alerts['other'].status = mock.Mock(return_value='test')

        status = self.dispatcher.status()
        self.assertEquals(['test', 'test'], status)


class TestWithEmail(testing.AsyncTestCase):
    def setUp(self):
        super(TestWithEmail, self).setUp()

        self.config = {'/foo': {'children': 1,
                                'alerter': {'email': 'unit@test.com',
                                            'body': 'Unit test body here.'}}}

        self._cs = mock.MagicMock()
        self.dispatcher = alerts.Dispatcher(self._cs, self.config)

    @testing.gen_test
    def test_dispatch_without_timeout(self):
        """Test dispatcher->EmailAlerter.alert() chain."""

        with mock.patch.object(alerts.email.EmailAlert,
                               '__init__') as mocked_email_alert:

            mocked_email_alert.return_value = None  # important for __init__

            yield self.dispatcher.update(
                data={'path': '/foo'},
                state='Error')

            # Assertion below does really care about the 'conn' variable, but
            # it's required for assert_called_with to be exact.
            mocked_email_alert.assert_called_with(
                subject='/foo is in the Error state.',
                body='Unit test body here.',
                email='unit@test.com',
                conn=self.dispatcher.alerts['email']._mail_backend
            )
