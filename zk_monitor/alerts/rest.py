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
import urllib

from tornado import httpclient

from zk_monitor.alerts import base
from zk_monitor.monitor import states

log = logging.getLogger(__name__)

HIPCHAT_API_URL = ('https://api.hipchat.com/v1/rooms/message'
                   '?format=json')


class HipchatAlerter(base.AlerterBase):
    """Send a notification to a HipChat room.

    For more details read the AlerterBase documentation.

    Expects the following configured alerter:

    >>> /services/food/barn
          alerter:
            hipchat:
             - room: Engineering
             - from: zk_monitor
             - token: <token>
           children: 1

    The "from" parameter will default to 'ZK Monitor' if not specified.
    """

    def __init__(self):
        self._async_client = None

    def _get_client(self):
        if not self._async_client:
            self._async_client = httpclient.AsyncHTTPClient()
            log.debug('Generating a new client: %s' % self._async_client)

        return self._async_client

    def style_from_state(self, state):
        """Returns color and icon based on `state`.

        Args:
            state: One of the monitor.states

        Returns:
            tuple of (color, icon)
        """

        styles = {
            states.OK: ('green', 'successful'),
            states.ERROR: ('red', 'failed')
        }

        default = ('gray', 'unknown')

        return styles.get(state) or default

    def _alert(self, path, state, message, params):
        http_client = self._get_client()

        color, icon = self.style_from_state(state)

        hc_body = {
            'auth_token': params['token'],
            'room_id': params['room'],
            'from': params.get('from', 'ZK Monitor'),
            'color': color,
            'message_format': 'text',
            'message': '(%s) %s is in %s - %s' % (icon, path, state, message)}

        hc_safe_body = urllib.urlencode(hc_body)

        log.debug('URL: %s' % HIPCHAT_API_URL)
        log.debug('BODY: %s' % hc_safe_body)
        request = httpclient.HTTPRequest(
            url=HIPCHAT_API_URL,
            method='POST',
            body=hc_safe_body)

        log.debug('Fetching RESTful api call: %s' % request)
        log.debug('client: %s' % http_client)
        http_client.fetch(request, self._handle_request)

    def _handle_request(self, response):
        if response.error:
            log.error('Response had an error: %s' % response.error)
        else:
            log.debug('Response successful: %s' % response.body)

        return not response.error
