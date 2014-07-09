# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Copyright 2014 Nextdoor.com, Inc

import logging

from tornadomail import message
from tornadomail.backends import smtp

from zk_monitor.alerts import base

log = logging.getLogger(__name__)


class EmailAlerter(base.AlerterBase):
    """Simple Email-based Alerter Object

    This object handles incoming alert calls from the main
    zk_monitor.monitor.Monitor class and converts them into email messages.
    Your zk_monitor YAML configuration file must include (for each path) a
    configured 'alerter' section like this:

        /services/foo/min_1:
          alerter:
            email: you@home.com
            body: Hey bob, fix this!
          children: 1
    """

    _saved_mail_backend = None

    @property
    def _mail_backend(self):
        """Returns a single EmailBackend object every time its called"""
        if not self._saved_mail_backend:
            self._saved_mail_backend = smtp.EmailBackend()

        return self._saved_mail_backend

    def _alert(self, message, params):
        """Send an email alert.

        args:
            message: Main message contents.
            params: A dictionary containing additional message params:
              { 'email': <email address to send alert to>,
                'body': <full message body> }
        """
        subject = message
        try:
            body = params['body']
            email = params['email']
        except (TypeError, KeyError):
            log.debug('Invalid configuration passed: %s' % params)
            return

        # Create the Alert object. The object takes care of everything from
        # here so we store no reference to it (and let it get garbage
        # collected on its own later)
        log.debug('Creating Email Alert Message: %s' % message)
        log.debug('Creating Email Alert with: %s' % EmailAlert)
        EmailAlert(
            subject=subject,
            body=body,
            email=email,
            conn=self._mail_backend)


class EmailAlert(object):
    """A single Email Alert."""
    def __init__(self, subject, body, email, conn):
        """Simple object for sending and tracking an email.

        args:
            subject: Subject of the message
            body: Body of the email
            email: Email Address to send to
            conn: smtp.EmailBackend instance
        """
        log.info('[%s] Message Instance Created' % subject)
        self._subject = subject

        # Send the message and register a callback to our helper method for
        # logging when the message has been sent.
        msg = message.EmailMessage(
            subject=subject,
            body=body,
            from_email='zk_monitor',
            to=[email],
            connection=conn)
        msg.send(callback=self._alertSent)

    def _alertSent(self, state):
        """Simple logging callback.

        Used just to ensure that when a message send is started, we also
        log whether or not the message send was successful.

        args:
            state: 0 if failed, 1 if successfull

        returns:
            Bool of send success (used mainly for unit testing)
        """
        if state == 1:
            log.info('[%s] Message Sent Successfully!' % self._subject)
            return True
        log.info('[%s] Message Send Failed!' % self._subject)
        return False
