import logging
import mock
import time

from tornado import gen
from tornado import testing
from tornado.ioloop import IOLoop

from zk_monitor.alerts import dispatcher
from zk_monitor.alerts import email
from zk_monitor.alerts import rest


log = logging.getLogger(__name__)


def mock_tornado(value=None):
    """Creates a mock for a coroutine function that returns `value`"""

    @gen.coroutine
    def call(*args, **kwargs):
        call._call_count = call._call_count + 1
        call._last_args = args
        call._last_kwargs = kwargs
        raise gen.Return(value)

    call._call_count = 0
    return call


def class_mock_tornado(value=None):
    """Creates a mock for a coroutine function that returns `value`"""

    @gen.coroutine
    def call(self, *args, **kwargs):
        call._call_count = call._call_count + 1
        call._last_args = args
        call._last_kwargs = kwargs
        raise gen.Return(value)

    call._call_count = 0
    return call


class TestDispatcher(testing.AsyncTestCase):
    def setUp(self):
        super(TestDispatcher, self).setUp()

        self.config = {'/bar': {'children': 1,
                                'cancel_timeout': 0.25,
                                'alerter': {'email': 'unit@test.com',
                                            'fake': 'unit test',
                                            'custom': 'something custom'}}}

        self._cs = mock.MagicMock(name='cluster.State')

    @gen.coroutine
    def sleep(self, seconds):
        # add_timeout is an "engine" function, so it has to be called as a Task
        yield gen.Task(IOLoop.current().add_timeout, time.time() + seconds)

    @testing.gen_test
    def test_dispatch_without_timeout(self):
        path = '/bar'
        config_no_timeout = self.config

        # This is the big difference between this text and the one with
        # cancellation.
        config_no_timeout[path]['cancel_timeout'] = None

        self.dispatcher = dispatcher.Dispatcher(self._cs, config_no_timeout)
        self.dispatcher.send_alerts = mock_tornado()

        # == First dispatch update with an error message
        update_task = self.dispatcher.update(
            path=path, state='Error', reason='Test')

        # Faking a pause between updates, otherwise this test executes too
        # quickly and the test may be invalid.
        yield self.sleep(seconds=0.01)

        # == Now simulate OK scenario which will cancel the alert.
        self.dispatcher.update(path=path, state='OK', reason='Test')

        # For the purpose of a unit test - wait for the first callback to
        # finish
        yield update_task

        # Make sure we fired off an alert.
        self.assertEquals(self.dispatcher.send_alerts._call_count, 2)

    @testing.gen_test
    def test_dispatch_with_cancellation(self):
        path = '/bar'
        self.dispatcher = dispatcher.Dispatcher(self._cs, self.config)
        self.dispatcher.send_alerts = mock.MagicMock()

        # == First dispatch update with an error message - this one will wait
        # for `cancel_timeout` seconds.
        update_task = self.dispatcher.update(
            path=path, state='Error', reason='Test')

        # Faking a pause between updates, otherwise this test executes too
        # quickly and the test may be invalid. This time has to be smaller than
        # the cancel_timeout above
        yield self.sleep(seconds=0.01)

        # == Now simulate OK scenario which will cancel the alert.
        self.dispatcher.update(path=path, state='OK', reason='Test')

        # For the purpose of a unit test - wait for the first callback to
        # finish
        yield update_task

        # Make sure we did NOT fire an alert.
        self.assertFalse(self.dispatcher.send_alerts.called,
                         "Alert should have been canceled.")

    @testing.gen_test
    def test_dispatch_with_now_in_spec(self):
        path = '/bar'
        self.dispatcher = dispatcher.Dispatcher(self._cs, self.config)
        self.dispatcher.send_alerts = mock_tornado()

        # == First dispatch update with an error message - this one will wait
        # for `cancel_timeout` seconds.
        yield self.dispatcher.update(
            path=path, state='Error', reason='Test')

        # This time has to be *greater* than the cancel_timeout above
        yield self.sleep(seconds=0.5)

        # Original alert was sent.
        self.assertEquals(self.dispatcher.send_alerts._call_count, 1)
        self.assertEquals(self.dispatcher.send_alerts._last_args, ('/bar',))

        # == Now simulate OK scenario which will cancel the alert.
        self.dispatcher.update(path=path, state='OK', reason='Test')

        # For the purpose of a unit test - wait for the first callback to
        # finish
        yield self.sleep(seconds=0.5)

        # Make sure we fired off an alert, and a followup
        self.assertEquals(self.dispatcher.send_alerts._call_count, 2)

    @testing.gen_test
    def test_dispatch_with_alert(self):
        path = '/bar'
        self.dispatcher = dispatcher.Dispatcher(self._cs, self.config)
        self.dispatcher.send_alerts = mock_tornado()

        # == First dispatch update with an error message - this one will wait
        # for 2 seconds.
        update_task = self.dispatcher.update(
            path=path, state='Error', reason='Test')

        # For the purpose of a unit test - wait for the first callback to
        # finish
        yield update_task

        self.assertEquals(self.dispatcher.send_alerts._last_args, (path,))

    @testing.gen_test
    def test_send_alerts(self):
        # Prepare for testing.
        # '/bar' is configued to use 'email' in self.config
        path = '/bar'
        self.dispatcher = dispatcher.Dispatcher(self._cs, self.config)
        self.dispatcher.alerts['email'] = mock.MagicMock()
        self.dispatcher.alerts['email'].alert = mock_tornado()
        self.dispatcher.alerts['custom'] = mock.MagicMock()
        self.dispatcher.alerts['custom'].alert = mock_tornado()

        # Set data, and send the alert
        self.dispatcher._path_status(path, message='unittest')
        yield self.dispatcher.send_alerts(path)

        # Dispatcher should loop through everything that is under "alerter"
        # setting. The 'fake' alerter should not cause any problems.

        # Email...
        self.assertEquals(
            self.dispatcher.alerts['email'].alert._last_kwargs,
            {'path': '/bar', 'state': 'Unknown', 'message': 'unittest',
             'params': self.config['/bar']['alerter']['email']})

        # Testing for custom alerts not real until all alerts are standardized.
        self.assertEquals(
            self.dispatcher.alerts['custom'].alert._last_kwargs,
            {'path': '/bar', 'state': 'Unknown', 'message': 'unittest',
             'params': self.config['/bar']['alerter']['custom']})

    @testing.gen_test
    def test_not_send_alerts(self):
        """Dispatcher should check if it's the alerting type."""

        path = '/bar'
        bad_cs = mock.MagicMock()
        bad_cs.getLock().status.return_value = False
        self.dispatcher = dispatcher.Dispatcher(bad_cs, self.config)
        self.dispatcher.alerts['email'] = mock.MagicMock()

        # Set data, and send the alert
        self.dispatcher._path_status(path, message='unittest')
        ret = yield self.dispatcher.send_alerts(path)

        self.assertFalse(ret)  # Did not send anything!

        # Email...
        self.dispatcher.alerts['email'].alert.assert_not_called()

    def test_lock(self):
        """Only one dispatcher should fire off alerts."""

        lock = mock.MagicMock()
        lock.status.side_effect = [True, False]
        self._cs.getLock.return_value = lock

        dispatcher1 = dispatcher.Dispatcher(self._cs, self.config)
        dispatcher2 = dispatcher.Dispatcher(self._cs, self.config)

        self.assertTrue(dispatcher1.status()['alerting'])
        self.assertFalse(dispatcher2.status()['alerting'])

    def test_status(self):
        """Dispatcher's status should report on all alerts that it uses."""

        self.dispatcher = dispatcher.Dispatcher(self._cs, self.config)
        self.dispatcher.alerts = {}
        self.dispatcher.alerts['email'] = mock.MagicMock()
        self.dispatcher.alerts['email'].status = mock.Mock(return_value='test')
        self.dispatcher.alerts['other'] = mock.MagicMock()
        self.dispatcher.alerts['other'].status = mock.Mock(return_value='test')

        status = self.dispatcher.status()
        self.assertItemsEqual(status['alerters'], ['other', 'email'])
        self.assertTrue('alerting' in status)


class TestWithEmail(testing.AsyncTestCase):
    def setUp(self):
        super(TestWithEmail, self).setUp()

        self.config = {'/foo': {'children': 1,
                                'alerter': {'email': 'unit@test.com'}}}

        self._cs = mock.MagicMock()
        self.dispatcher = dispatcher.Dispatcher(self._cs, self.config)

    @testing.gen_test
    def test_dispatch_without_timeout(self):
        """Test dispatcher->EmailAlert.alert() chain."""

        with mock.patch.object(email.EmailAlert,
                               '__init__') as mocked_email_alert:

            mocked_email_alert.return_value = None  # important for __init__

            yield self.dispatcher.update(
                path='/foo', state='Error', reason='Detailed reason')

            # Assertion below does really care about the 'conn' variable, but
            # it's required for assert_called_with to be exact.
            mocked_email_alert.assert_called_with(
                subject='Warning! /foo has an alert!',
                body='Detailed reason\n/foo is in the Error state.',
                email='unit@test.com',
                conn=self.dispatcher.alerts['email']._mail_backend
            )


class TestWithHipchat(testing.AsyncTestCase):
    def setUp(self):
        super(TestWithHipchat, self).setUp()

        self.config = {'/foo': {'children': 1,
                                'alerter': {
                                    'hipchat': {
                                        'token': '123',
                                        'room': 'UnitTest'}}}}

        self._cs = mock.MagicMock()

    @testing.gen_test
    def test_dispatch_without_timeout(self):
        """Test dispatcher->HipchatAlerter.alert() chain."""

        with mock.patch.object(rest.HipchatAlerter, '_alert',
                               class_mock_tornado()) as mocked_alerter:

            self.dispatcher = dispatcher.Dispatcher(self._cs, self.config)

            yield self.dispatcher.update(
                path='/foo', state='Error', reason='Detailed reason')

            # Assertion below does really care about the 'conn' variable, but
            # it's required for assert_called_with to be exact.
            self.assertEquals(
                mocked_alerter._last_args,
                ('/foo', 'Error', 'Detailed reason',
                 self.config['/foo']['alerter']['hipchat']))
