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
    def __init__(self):
        """Initialize the Alerter."""

        # Using __class__.__name__ here to specify the name of the child
        # classes that inherit this method.
        log.debug('Initializing Alerter "%s"' % self.__class__.__name__)

    def alert(self, message, params=None):
        """Fires off an Alert.

        args:
            message: String to send
            params: Dictionary of arbitrary parameters needed for specific
                    alert type.
        """
        # Using __class__.__name__ here to specify the name of the child
        # classes that inherit this method.
        log.warning('Firing Alert of type `%s` with "%s"' % (
            self.__class__.__name__, message))

        self._alert(message, params=params)
