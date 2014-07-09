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
import time

from tornado import gen
from tornado.ioloop import IOLoop

from zk_monitor.alerts import email
from zk_monitor.alerts import actions
from zk_monitor.monitor import states


log = logging.getLogger(__name__)


class Dispatcher(object):
    """Handles timing/cancelling/dispatching/dedup of all alerts to Alerter."""

    def __init__(self, cluster_state, config):
        """Set up local 'cache' of path meta data and available alerters.

        We only allow a single Dispatcher to alert in a given cluster of
        zkmonitor servers. We do this by acquiring a lock on a unique Zookeeper
        path for this cluster of zkmonitor machines.

        This prevents multiple alerts from being fired when a state change
        occurs, as only one Dispatcher object in the cluster of machines is
        active at ay time.

        Args:
            cluster_state: an instance of cluster.State
            config: dictionary containing paths and configuration such as
                {'/foo': {'children': 1,
                          'alerter': {'email': 'unit@test.com',
                                      'body': 'Unit test body here.'}}}

        """
        log.debug('Initiating Dispatcher.')

        self._live_path_status = {}
        self._config = config
        self._cluster_state = cluster_state

        self.alerts = {}
        self.alerts['email'] = email.EmailAlerter()

        self._begin_lock()

    def _begin_lock(self):
        """Begin monitoring the lock status path."""

        log.debug('Attempting to acquire lock for sending alerts.')
        self._lock = self._cluster_state.getLock('alerter')
        self._lock.acquire()

    @gen.coroutine
    def update(self, path, state, reason):
        """Update path meta data and maybe alert.

        This method should be thought of in 3 steps:
            1) Create a pending alert status
            2) Wait to see if it gets cancelled
            3) Check the status and alert.
        """
        # import monitor here? otherwise circular loop
        if state == states.OK:
            # Cancel the alert and bail out of here.
            self._path_status(path, message=reason, next_action=actions.NONE)
            raise gen.Return()

        # Set the alert, and continue to check your timer
        self._path_status(path, message=reason, next_action=actions.ALERT)

        # Check if we should timeout
        config = self._config[path]
        # TODO: Should be able to set a 'default' timeout for all paths where a
        # specifric cancel_timeout is not set.
        # TODO: refactor to self.get_config(path, value)
        # to check for default value, then grab path-specific value
        sleep_seconds = config.get('cancel_timeout', 0)

        yield self.sleep(sleep_seconds)

        # Re-fetch the status here -- it's important
        status = self._path_status(path)

        action = status['next_action']

        log.debug('Action required by %s: "%s"' % (state, action))
        if action == actions.ALERT:
            self.send_alerts(path)

        raise gen.Return()

    @gen.coroutine
    def sleep(self, seconds):
        """Do nothing for `seconds`, then continue the IO loop.

        If `seconds` is 0 or evaluates to 0 then this method exits immediately.
        """

        try:
            sleep_seconds = float(seconds)
        except (TypeError, ValueError):
            sleep_seconds = 0

        if sleep_seconds > 0:
            # add_timeout is a tornado "engine" function with a callback so it
            # has to be called as a gen.Task
            yield gen.Task(IOLoop.current().add_timeout,
                           time.time() + sleep_seconds)

        raise gen.Return()

    def send_alerts(self, path):
        """Send alert regarding this data."""
        message = self._path_status(path)['message']

        config = self._config[path]
        for alert_type, params in config['alerter'].items():
            alert_engine = self.alerts.get(alert_type, None)

            if not alert_engine:
                log.error('Alert type `%s` specified '
                          'but not available' % alert_type)
                continue

            log.debug('Invoking alert type `%s`.' % alert_type)

            # Making `body` optional. `message` is used as subject by the email
            # engine.
            body = config['alerter'].get('body', message)

            # NOTE: Assuming email engine here until we can generalize it.

            email_params = {'body': body,
                            'email': config['alerter']['email']}
            alert_engine.alert(message=message,
                               params=email_params)

    def _path_status(self, path, message=None, next_action=None):
        """Get or create meta data for specific data path.

        Args:
            path: Some zk registered path /foo
            message: Human readable message/reason for an action.
            next_action: alerts.actions value
        """

        if path not in self._live_path_status:
            self._live_path_status[path] = {
                'message': False,
                'next_action': None}

        path_data = self._live_path_status[path]
        if message:
            path_data['message'] = message

        if next_action:
            path_data['next_action'] = next_action

        return path_data

    def status(self):
        """Return status of the dispatcher and alerts.

        This is invoked by the web server for /status page.
        """

        alerter_list = self.alerts.keys()
        lock = self._lock.status()

        return {
            'alerters': alerter_list,
            'alerting': lock,
        }
