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

from zk_monitor.monitor import states

log = logging.getLogger(__name__)


class InvalidConfigException(Exception):
    pass


class Monitor(object):
    """Main object used for monitoring nodes in Zookeeper."""

    def __init__(self, dispatcher, ndsr, cs, paths):
        """Initialize the object and our watches.

        args:
            ndsr: A KazooServiceRegistry object
            cs: cluster.State object
            paths: A dict of paths to monitor.
                   eg: { '/foo': { 'children': 1 },
                         '/bar': { 'children': 2 } }
        """
        log.debug('Initializing Monitor with Service Registry %s' % ndsr)
        self._dispatcher = dispatcher
        self._ndsr = ndsr
        self._cs = cs
        self._paths = paths

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
        """Executed when one of our watched paths is updated.

        This method receives updates from the Service Registry when
        a path changes, calls out to the _get_compliance() method, and
        updates the dispatcher with the new status and message.

        args:
            data: The data returned by the Service Registry.
        """
        path = data['path']

        new_state, reason = self._get_compliance(path)

        # NOTE: temporarily grab the old state, then update local knowledge to
        # the new state. We need both (old and new) states to make a decision
        # later, but the old one is stored in this object, and the new one is
        # available only when coming into this method.
        old_state = self._path_state(path)
        self._path_state(path, new_state)

        log.debug('Path %s changed from %s to %s' % (
            path, old_state, new_state))
        if self._should_update_dispatcher(old_state, new_state):
            # NOTE: update() will return a reference to an async task
            # This code doesn't use it, but if the caller of this method
            # wants to do something regarding this update (unit tests!)
            # then it needs to be able to wait for it.
            # *Must* return this reference.
            return self._dispatcher.update(
                path=path, state=new_state, reason=reason)

    def _get_compliance(self, path):
        """Check if a given path is currently within spec.

        args:
            path: The path to validate (must exist in self._paths)

        returns: tuple
            monitor.states: Message describing current status.
            string: reason for the state above.
        """
        # Begin with no errors
        state = states.UNKNOWN
        reason = 'No information is available about this path.'

        # Load up the requirements for this path
        config = self._paths[path]

        # If there is a minimum 'children' amount, check that.
        if config and 'children' in config:
            # TODO: Pass in all needed data to _get_compliance() so it doesn't
            # make direct SR calls.
            count = len(self._ndsr.get(path)['children'])
            log.debug('Comparing %s min children (%s) to current count (%s).' %
                      (path, config['children'], count))
            if count < config['children']:
                state = states.ERROR
                reason = ('%s children is less than minimum %s' %
                          (count, config['children']))
                log.debug(reason)
            else:
                state = states.OK
                reason = 'All checks pass.'

        # Done checking things..
        return state, reason

    def _should_update_dispatcher(self, old_state, new_state):
        # Most conditions should update the dispatcher except a couple

        silent_conditions = [
            (states.UNKNOWN, states.OK),
            (states.OK, states.OK),
        ]

        if (old_state, new_state) in silent_conditions:
            # If transition from old to new state is something that we want to
            # handle silently, then do not update the dispatcher
            return False

        # For all other cases - update it.
        return True

    def _path_state(self, path, new_state=None):
        """Get or set a local knowledge of a path state."""

        if new_state:
            self._paths[path]['state'] = new_state

        return self._paths[path].get('state', states.UNKNOWN)

    def status(self):
        """Returns a dict with our current status."""
        # Begin our status dict
        status = {}

        # For every path we are watching, get the live compliance status
        status['compliance'] = {}

        for path in self._paths:
            state, reason = self._get_compliance(path)
            status['compliance'][path] = {}
            status['compliance'][path]['state'] = state
            status['compliance'][path]['message'] = reason

        # Return the whole thing
        return status
