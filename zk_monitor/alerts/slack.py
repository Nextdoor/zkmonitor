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
:mod:`zk_monitor.alerts.slack`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sends Alerter messages to Slack channels.
"""

import logging

from tornado import gen

from tornado_rest_client.clients import slack
from tornado_rest_client import exceptions

from zk_monitor.alerts import base
from zk_monitor.monitor import states

log = logging.getLogger(__name__)

__author__ = 'Matt Wise <matt@nextdoor.com>'


class SlackAlerter(base.AlerterBase):

    """Sends a notification to a Slack channel.

    For more details read the AlerterBase documentation.

    Expects the following configured alerter:

        >>> /services/food/barn:
              alerter:
                slack:
                  - channel: #oncall
                  - from: zk_monitor
                  - token: <token>
                children: 1

    The 'from' parameter will default to 'ZK Monitor' if not specified.
    """

    def style_from_state(self, state):
        """Returns icon based on `state`.

        :params monitor.states state: A state from :mod:`monitor.states`
        :return: icon_emoji
        :rtype: string
        """
        styles = {
            states.OK: ':+1:',
            states.ERROR: ':exclamation:'
        }

        default = ':grey_question:'

        return styles.get(state) or default

    @gen.coroutine
    def _alert(self, path, state, message, params):
        client = slack.Slack(token=params['token'])
        post_message = client.chat_postMessage()

        icon = self.style_from_state(state)

        status = None
        try:
            res = yield post_message.http_post(
                channel=params['channel'],
                text='(%s) %s is in %s - %s' % (icon, path, state, message),
                as_user=params.get('from', 'ZK Monitor'))
            status = client.check_results(res)

        except exceptions.BaseException as e:
            log.critical('Alert to Slack failed: %s' % e)

        raise gen.Return(status)
