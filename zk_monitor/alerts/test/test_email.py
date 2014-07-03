import mock

from tornado.testing import unittest

from zk_monitor.alerts import email


class TestEmailAlerter(unittest.TestCase):
    def setUp(self):
        self.mocked_cs = mock.MagicMock()
        self.mocked_lock = mock.MagicMock()
        self.mocked_cs.getLock.return_value = self.mocked_lock
        self.alerter = email.EmailAlerter(self.mocked_cs)

    @mock.patch('tornadomail.backends.smtp.EmailBackend')
    @mock.patch('zk_monitor.alerts.email.EmailAlert')
    def testAlert(self, mocked_alert, mocked_backend):
        backend_instance = mocked_backend.return_value
        params = {
            'body': 'Unit Test Body',
            'email': 'unit@test.com',
        }
        self.alerter._alert('Unit Test Message', params)
        mocked_alert.assert_called_with(
            subject='Unit Test Message',
            body='Unit Test Body',
            email='unit@test.com',
            conn=backend_instance)

    def testAlertWithBadParams(self):
        self.assertEquals(None, self.alerter.alert('unittest', params=None))
        self.assertEquals(None, self.alerter.alert('unittest', params={}))

    def testSingleBackend(self):
        once = self.alerter._mail_backend
        twice = self.alerter._mail_backend
        self.assertEqual(once, twice)


class TestEmailAlert(unittest.TestCase):
    def setUp(self):
        self.msg = 'unit test msg'
        self.body = 'unit test body'
        self.email = 'unit@test.com'
        self.conn = mock.MagicMock()

    @mock.patch('tornadomail.message.EmailMessage')
    def testInit(self, mocked_message):
        email.EmailAlert(self.msg, self.body, self.email, self.conn)
        mocked_message.assert_called_with(
            subject=self.msg,
            body=self.body,
            to=[self.email],
            from_email='zk_monitor',
            connection=self.conn)

    @mock.patch('tornadomail.message.EmailMessage')
    def testAlertSent(self, mocked_message):
        alert = email.EmailAlert(self.msg, self.body, self.email, self.conn)
        self.assertEquals(True, alert._alertSent(1))
        self.assertEquals(False, alert._alertSent(0))
