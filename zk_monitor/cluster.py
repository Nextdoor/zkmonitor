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
Agent-to-Agent Cluster communication engine.

This class manages all of the communication between zk_monitor agents
(using Zookeeper as the communication system). Handles all direct writes
from zk_monitor into Zookeeper in one common module.
"""

import logging
import platform
import os

log = logging.getLogger(__name__)


class ClusterException(Exception):
    """Thrown when the Cluster state engine has an exception."""


class State(object):
    """Cluster State Engine"""

    def __init__(self, ndsr, path):
        """Initialize the Cluster State Engine.

        args:
            ndsr: A Service Registry object
            path: Path in Zookeeper for storing configuration state
        """
        # Store our unique cluster path name and service registry objects
        self._path = path
        self._ndsr = ndsr
        log.info('Initializing Cluster State Engine at %s' % self._path)

        # Generate a unique name for this particular process of zk_monitor
        self._name = '%s-%s' % (platform.node(), os.getpid())

        # Register ourselves as a monitoring agent. If this fails with a
        # nd_service_registry.exceptions.ReadOnly exception, we throw a
        # log event and raise the execption. The app can continue to run
        # in a degraded state (no cluster support).
        self._register_myself()

    def _register_myself(self):
        """Register myself as a zk_monitor agent."""
        self._ndsr.set_node('%s/agents/%s' % (self._path, self._name))

    def getLock(self, name):
        """Retreives an async Service Registry Lock object.

        args:
            name: Name of the path to acquire the lock from

        returns:
            nd_service_registry.lock.Lock object
        """
        lock_path = '%s/locks/%s' % (self._path, name)
        return self._ndsr.get_lock(lock_path, self._name, wait=0)
