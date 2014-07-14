# Zookeeper Node Monitoring Daemon

![Build Status](https://api.travis-ci.org/Nextdoor/zkmonitor.png?branch=master)
![# of downloads](https://pypip.in/d/zk_monitor/badge.png)
![pypy version](https://badge.fury.io/py/zk_monitor.png)


This is a simple daemon for monitoring particular Zookeeper nodes for
compliance with a given set of specifications (ie, minimum number of
registered nodes). In the event that a path changes and becomes out of
spec, (too few nodes, for example), an alert is fired off to let you know.

## Clustered Design

*zk_monitor* is designed to operate in clustered mode with multiple redundant
agents running on multiple servers. The agents talk to eachother through
Zookeeper using a common path and a series of locks/znodes. You can run as
many agents as you want, but only one will ever handle sending off alerts.

## Configuration

Most of the connection and *zk_monitor* specific settings are managed via
CLI arguments:

    $ python runserver.py --help
    Usage: runserver.py <options>
    
    Options:
      --version             show program's version number and exit
      -h, --help            show this help message and exit
      -z ZOOKEEPER, --zookeeper=ZOOKEEPER
                            Zookeeper Server (def: localhost:2181)
      --zookeeper_user=ZOOKEEPER_USER
                            Zookeeper ACL Username
      --zookeeper_pass=ZOOKEEPER_PASS
                            Zookeeper ACL Password
      -c CLUSTER_NAME, --cluster_name=CLUSTER_NAME
                            Unique cluster name (ie, prod-zookeeper-monitor)
      --cluster_prefix=CLUSTER_PREFIX
                            Prefix path in Zookeeper for all zk_monitor clusters
      -f FILE, --file=FILE  Path to YAML file with znodes to monitor.
      -p PORT, --port=PORT  Port to listen to (def: 8080)
      -l LEVEL, --level=LEVEL
                            Set logging level (INFO|WARN|DEBUG|ERROR)
      -s SYSLOG, --syslog=SYSLOG
                            Log to syslog. Supply facility name. (ie "local0")

The list of paths that you want to monitor are supplied via a YAML
formatted configuration file. Here's an example file:

    /services/foo/min_1:
      alerter:
        email: you@home.com
      children: 1
    /services/foo/min_0:
      alerter:
        email: your_buddy@home.com
      children: 0
    /services/foo/min_3:
      children: 3

### Alerter Configuration

In the above example, you'll see that two of the paths have an 'alerter/email'
parameter configured. With this in place, any path spec violations will result
in an email fired off to that address. The third path does not have any
settings, which means that no alert will actually be sent off in the event of
a spec violation.

### Simple Execution

    $ python runserver.py -l INFO -z localhost:2181 -f test.yaml
    2014-05-31 16:20:25,862 [35661] [nd_service_registry] [__init__]: (INFO) Initializing ServiceRegistry object
    2014-05-31 16:20:25,863 [35661] [nd_service_registry] [_connect]: (INFO) Connecting to Zookeeper Service (localhost:2181)
    2014-05-31 16:20:25,867 [35661] [nd_service_registry] [_state_listener]: (INFO) Zookeeper connection state changed: CONNECTED
    2014-05-31 16:20:25,868 [35661] [nd_service_registry] [__init__]: (INFO) Initialization Done!
    2014-05-31 16:20:25,868 [35661] [zk_monitor.monitor] [_stateListener]: (INFO) Service registry connection state: True

## REST Interface

Though not necessary for alerting purposes, you can access the a JSON-formatted
REST interface for the intentionally inspecting the status of the app, and
the current compliance of your watched Zookeeper nodes.

### /status

This page provides a simple live status of the app and its monitors.

    $ curl --silent  http://localhost:8080/status | python -m json.tool
    {
        "monitor": {
            "alerter": {
                "alerting": true
            },
            "compliance": {
                "/services/foo/min_0": true,
                "/services/foo/min_1": "Found children (0) less than minimum (1)",
                "/services/foo/min_3": "Found children (2) less than minimum (3)"
            }
        },
    "version": "0.0.1",
        "zookeeper": {
            "connected": true
        }
    }

## Development

### Class/Object Architecture

    runserver
    |
    +-- nd_service_registry.KazooServiceRegistry
    |   | Connection to Zookeeper
    |
    +-- alert.Dispatcher
    |   | Handles dispatching of all alerts to Alerter objects
    |   |
    |   +-- alerts.email.EmailAlerter
    |   |   | Sends Email-Based Alerts Asynchronously
    |   |   |
    |   |   +-- tornadomail.backends.smtp.EmailBackend()
    |   |
    |   +-- alerts.rest.HipChatAlerter
    |       | Sends Hipchat Alerts Asynchronously
    |
    +-- cluster.State
    |   | Handles node-to-node communication via Zookeeper
    |   |
    |   +-- Registers /zk_monitor/agent/<agent name>
    |
    +-- monitor.Monitor
    |   | Monitors all configured paths
    |   |
    |   +-- Obj Ref -> alerts.Dispatcher
    |       | Alerts are fired off to the Dispatcher, the Dispatcher
    |       | handles determining whether or not the alert is a dup, a shift
    |       | from in-compliance to out-of-compliance (or vice versa),
    |       | and which Alerters to fire off (Hipchat, Email, etc).
    |
    +-- tornado.Application
    |   | Handles all web requests
    |   |
    |   +-- web.app.getApplication()
    |       |
    |       +-- root.RootHandler
    |       |   URL: /
    |       |
    |       +-- state.StateHandler
    |       |   URL: /state
    |       |   Obj Ref -> nd_service_registry.KazooServiceRegistry
    |       |   Obj Ref -> monitor.Monitor

### Setup

    # Create a dedicated Python virtual environment and source it
    virtualenv --no-site-packages .venv
    unset PYTHONPATH
    source .venv/bin/activate

    # Install the dependencies
    make build

    # Run the tests
    make test


### Postfix on Mac OSX

If you want to develop on a Mac OSX host, you need to enable email the
*postfix* daemon on your computer. Here's how!

Modify */Syatem/Library/LaunchDaemons/org.postfix.master.plist*:

    --- /System/Library/LaunchDaemons/org.postfix.master.plist.bak	2014-06-02 11:45:24.000000000 -0700
    +++ /System/Library/LaunchDaemons/org.postfix.master.plist	2014-06-02 11:47:07.000000000 -0700
    @@ -9,8 +9,6 @@
            <key>ProgramArguments</key>
            <array>
                   <string>master</string>
    -              <string>-e</string>
    -              <string>60</string>
            </array>
            <key>QueueDirectories</key>
            <array>
    @@ -18,5 +16,8 @@
            </array>
            <key>AbandonProcessGroup</key>
            <true/>
    +
    +        <key>KeepAlive</key>
    +       <true/>
     </dict>
     </plist>

Restart the service:

    cd /System/Library/LaunchDaemons
    sudo launchctl unload org.postfix.master.plist 
    sudo launchctl load org.postfix.master.plist
