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

log = logging.getLogger(__name__)


class Dispatcher(object):
    """Handles timing/cancelling/dispatching/dedup of all alerts to Alerter."""

    # This dictionary is shared by multiple coroutines.
    _live_data_status = {}

    alerts = {}

    def __init__(self, cluster_state, config):
        """Set up local 'cache' of path meta data and available alerters."""
        log.debug('Initiating Dispatcher.')

        self._live_data_status = {}
        self._config = config
        self._cluster_state = cluster_state

        self.alerts = {}
        self.alerts['email'] = email.EmailAlerter(cluster_state)

    @gen.coroutine
    def update(self, data, state):
        """Update path meta data and maybe alert.

        Data gets updated via the helper _update() method, which returns
        an appropriate action asyncronously. Read _update doc for cancellation
        process details.

        An action governs whether to send an alert or not.
        """

        # TODO: FIXME: this asyn call isn't actually helping the Monitor
        # routine because we yield here to take an action
        action = yield gen.Task(self._update, data, state)

        if action:
            self.send_alerts(data)

        raise gen.Return()

    @gen.coroutine
    def _update(self, data=None, state=None):
        """Updates the state of datas and concludes whether to alert or not."""

        # Generate report message.
        message = '%s is %s' % (data['path'], state)

        # import monitor here? otherwise circular loop
        if state == 'OK':
            # Cancel the alert and bail out of here.
            self.set_status(data, message=message, next_action=None)
            raise gen.Return(None)

        # Set the alert, and continue to check your timer
        self.set_status(data, message=message, next_action='alert')

        # Check if we should timeout
        config = self._config[data['path']]
        cancel_timeout = config.get('cancel_timeout', 0)
        try:
            cancel_timeout = float(cancel_timeout)
        except (TypeError, ValueError):
            cancel_timeout = 0

        if cancel_timeout > 0:
            # Async version of "sleep"
            yield gen.Task(IOLoop.current().add_timeout,
                           time.time() + cancel_timeout)

        # Re-fetch the status here -- it's important
        status = self.get_status(data)

        raise gen.Return(status['next_action'])

    def send_alerts(self, data):
        """Send alert regarding this data."""
        path = data['path']
        message = self.get_status(data)['message']

        config = self._config[path]
        for alert_type, params in config['alerter'].items():
            alert_engine = self.alerts.get(alert_type, None)

            if not alert_engine:
                log.error('Alert type %s specified but not available')
                continue

            # NOTE: Assuming email engine here until we can generalize it.
            email_params = {'body': config['alerter']['body'],
                            'email': config['alerter']['email']}
            alert_engine.alert(message=message,
                               params=email_params)

    def set_status(self, data, **kwargs):
        """Create or update meta data for specific data path."""

        self._live_data_status[data['path']] = self.get_status(data)

        path = self._live_data_status[data['path']]
        if 'message' in kwargs:
            path['message'] = kwargs['message']

        if 'next_action' in kwargs:
            path['next_action'] = kwargs['next_action']

    def get_status(self, data):
        """Fetch meta data for a specific data path, or return a template."""

        default = {
            'message': False,
            'next_action': None}
        return self._live_data_status.get(data['path'], default)

    def status(self):
        """Return status of the dispatcher and alerts.

        This is invoked by the web server for /status page.
        """

        return [alert.status() for name, alert in self.alerts.items()]
