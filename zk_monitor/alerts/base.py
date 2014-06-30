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

log = logging.getLogger(__name__)


class AlerterBase(object):
    """Base Alerter Object.

    This is not meant to be instantiated, but provides the common public
    functions for any Alerter object and the general behavior we expect.
    """
    def __init__(self, cs):
        """Initialize the Alerter.

        We only allow a single Alerter to operate in a given cluster of
        zkmonitor servers. We do this by acquiring a lock on a unique
        Zookeeper path for this cluster of zkmonitor machines.

        This prevents multiple alerts from being fired when a state change
        occurs, as only one Alerter object in the cluster of machines is
        active at ay time.

        args:
            cs: cluster.State object
        """
        log.debug('Initializing Alerter')
        self._cs = cs

        # Begin getting our lock. If the lock is busy, we'll wait silently
        # for the lock to be acquired before se send out alerts.
        self._begin_lock()

    def _begin_lock(self):
        """Begin monitoring the lock status path.

        args:
            path: Zookeeper path to find our lock in.
        """
        # FIXME: Bug here -- multiple classes inheriting from this, but only 1
        # will get this lock. Meaning that if we have Email and Hipchat - only
        # one of the two will work
        log.debug('Attempting to acquire lock for sending alerts.')
        self._lock = self._cs.getLock('alerter')
        self._lock.acquire()

    def status(self):
        """Returns the current status of this Alerter object.

        returns:
            Dict that looks like:

            { 'alerting': <bool> }
        """
        return {
            'alerting': self._lock.status()
        }

    def alert(self, message, params=None):
        """Fires off an Alert.

        If this Alerter object currently owns the 'alert lock', then
        this function calls the self._alert() method of the Alerter
        to send off a message.

        args:
            message: String to send
        """
        if not self._lock.status():
            log.debug('Not the primary alerter, not sending message: %s' %
                      message)
            return

        log.warning('Firing Alert: %s' % message)
        self._alert(message, params=params)
