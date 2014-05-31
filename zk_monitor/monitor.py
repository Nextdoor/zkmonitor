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

from tornado import gen

log = logging.getLogger(__name__)


class InvalidConfigException(Exception):
    pass


class Monitor(object):
    """Main object used for monitoring nodes in Zookeeper."""
    def __init__(self, ndsr, paths):
        """Initialize the object and our watches.

        args:
            ndsr: A KazooServiceRegistry object
            paths: A dict of paths to monitor.
                   eg: { '/foo': { 'children': 1 },
                         '/bar': { 'children': 2 } }
        """
        log.debug('Initializing Monitor with Service Registry %s' % ndsr)
        self._ndsr = ndsr

        # Validate the supplied path configs
        self._validatePaths(paths)

        # Immediately register a watcher on the connection state
        self._state = self._ndsr.get_state(self._stateListener)

        # Generate watches on those paths
        self._watchPaths(paths.keys())
        self._paths = paths

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
                raise InvalidConfigException('Invalid children setting: %s' %
                        config['children'])


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
        for path in paths:
            log.debug('Asking to watch %s' % path)
            self._ndsr.get(path)

    def _verifyCompliance(self, path):
        """Verify whether a given path is currently within spec.

        args:
            path: The path to validate (must exist in self._paths)

        returns:
            True: Everything is happy

            or

            A string describing the failure.
        """
        # Begin with compliance being True
        compliant = True

        # Load up the requirements for this path
        config = self._paths[path]

        # If the config is empty, then there is no compliance testing.
        if not config:
            return compliant

        # If there is a minimum 'children' amount, check that.
        if 'children' in config:
            count = len(self._ndsr.get(path)['children'])
            log.debug('Comparing %s min children (%s) to current count (%s).' %
                      (path, config['children'], count))
            if count < config['children']:
                return ('Found children (%s) less than minimum (%s)' %
                       (count, config['children']))

        # Done checking things..
        return compliant

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
