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
"""
Initiates monitoring Zookeeper paths for compliance.

This modules focus is to initiate the monitoring of the paths in Zookeeper, and
keep track of them for their current 'compliance state.' Upon any change to
their state, compliance is validated and the appropriate alerts are dispatched.
"""

import logging

from zk_monitor import alerts
from zk_monitor.alerts import email

log = logging.getLogger(__name__)


class InvalidConfigException(Exception):
    pass


class Monitor(object):
    """Main object used for monitoring nodes in Zookeeper."""

    def __init__(self, ndsr, cs, paths):
        """Initialize the object and our watches.

        args:
            ndsr: A KazooServiceRegistry object
            cs: cluster.State object
            paths: A dict of paths to monitor.
                   eg: { '/foo': { 'children': 1 },
                         '/bar': { 'children': 2 } }
        """
        log.debug('Initializing Monitor with Service Registry %s' % ndsr)
        self._ndsr = ndsr
        self._cs = cs
        self._paths = paths

        # Temporary duplicating these until the separation is in place
        # self._config = paths

        # Create our Alerter object. All notifications of path compliance
        # being out of spec are sent off to an Alerter.
        # TODO(Fix this path)
        self._alerter = email.EmailAlerter(self._cs)

        self._dispatcher = alerts.Dispatcher(
            cluster_state=self._cs,
            config=self._paths)

        # Validate the supplied path configs
        self._validatePaths(paths)

        # Immediately register a watcher on the connection state
        self._state = self._ndsr.get_state(self._stateListener)

        # Generate watches on those paths
        self._watchPaths(paths.keys())

    def _stateListener(self, state):
        """Executed any time the connection state changes.

        args:
            state: Boolean of the new connection state.
        """
        log.info('Service registry connection state: %s' % state)
        self._state = state

    def _validateConfig(self, config):
        """Validate a single path configuration setting.

        args:
            config: A dict with the path and the appropriate settings.
                    eg. { 'children': 1, }

        raises:
            InvalidConfigException: If the configuration config is invalid.
        """
        log.debug('Validating supplied config: %s' % config)

        # If there are no config keys at all, then we just watch the
        # path and do nothing with it.
        if not config:
            return

        # if there is a children setting, ensure its a number
        if 'children' in config:
            if not isinstance(config['children'], int):
                raise InvalidConfigException(
                    'Invalid children setting: %s' % config['children'])

    def _validatePaths(self, paths):
        """Validate a dict of paths/configs.

        args:
            paths: A dict of paths to monitor.
                   eg: { '/foo': { 'children': 1 },
                         '/bar': { 'children': 2 } }

        raises:
            InvalidConfigException: If any part of the config is invalid.
        """
        log.debug('Validating supplied paths: %s' % paths)

        if not paths:
            return

        for path, config in paths.iteritems():
            try:
                self._validateConfig(config)
            except InvalidConfigException, e:
                log.error('Error reading config for path %s: %s' % (path, e))
                raise

    def _watchPaths(self, paths):
        """Add a series of Zookeeper watches for the paths supplied.

        args:
            paths: A list of paths to watch
        """

        # Now begin watching our paths, using the above callback
        # function when a path is updated.
        for path in paths:
            log.debug('Asking to watch %s' % path)
            self._ndsr.get(path, callback=self._pathUpdateCallback)

    def _pathUpdateCallback(self, data):
        """Quick method executed when one of our watched paths (defined below)
        is updated. This method receives updates from the Service Registry when
        a path changes, calls out to the _verifyCompliance() method, and
        updates the dispatcher with the new status and message.

        args:
            data: The data returned by the Service Registry.
        """
        path = data['path']
        log.debug('Path change detected at %s' % path)

        message = self._verifyCompliance(path)

        if self._should_dispatch_alert(data):
            self._dispatcher.update(data=data,
                                    message=message)

    def _verifyCompliance(self, path):
        """Verify whether a given path is currently within spec.

        args:
            path: The path to validate (must exist in self._paths)

        returns:
            False: No failures are found / Nothing to report.
            or
            String: Message describing the failure.
        """
        # Begin with no errors
        errors = False

        # Load up the requirements for this path
        config = self._paths[path]

        # If the config is empty, then there is no compliance testing.
        if not config:
            return errors

        # If there is a minimum 'children' amount, check that.
        if 'children' in config:
            count = len(self._ndsr.get(path)['children'])
            log.debug('Comparing %s min children (%s) to current count (%s).' %
                      (path, config['children'], count))
            if count < config['children']:
                msg = ('Found children (%s) less than minimum (%s)' %
                       (count, config['children']))
                return msg

        # Done checking things..
        return errors

    def _should_dispatch_alert(self, data):
        # this function would check for circumstances that shouldn't alert
        # such as transition from Good to Good, or from Unknown to Good
        return True

    def state(self):
        """Returns a dict with our current status."""
        # Begin our status dict
        status = {}

        # For every path we are watching, get the live compliance status
        status['compliance'] = {}
        for path in self._paths:
            status['compliance'][path] = self._verifyCompliance(path)

        # Return the whole thing
        return status
