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
# Copyright 2014 Nextdoor.com

"""
"""

__author__ = 'matt@nextdoor.com (Matt Wise)'

import logging

from tornado import web

from zk_monitor import utils
from zk_monitor.web import root
from zk_monitor.web import state

log = logging.getLogger(__name__)


def getApplication(ndsr, monitor, dispatcher):
    # Group our passed in options into a common settings dict
    settings = {
        'ndsr': ndsr,
        'monitor': monitor,
        'dispatcher': dispatcher,
    }

    # Default list of URLs provided by Hooky and links to their classes
    URLS = [
        # Handle initial web clients at the root of our service.
        (r"/", root.RootHandler),

        # Handle initial web clients at the root of our service.
        (r"/status", state.StatusHandler, dict(settings=settings)),

        # Provide access to our static content
        (r'/static/(.*)', web.StaticFileHandler,
            {'path': utils.getStaticPath()}),

        # Handle incoming hook requests
    ]
    application = web.Application(URLS)
    return application
