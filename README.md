# Zookeeper Node Monitoring Daemon

This is a simple daemon for monitoring particular Zookeeper nodes for
compliance with a given set of specifications (ie, minimum number of
registered nodes). In the event that a path changes and becomes out of
spec, (too few nodes, for example), an alert is fired off to let you know.

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
      -f FILE, --file=FILE  Path to YAML file with znodes to monitor.
      -p PORT, --port=PORT  Port to listen to (def: 8080)
      -l LEVEL, --level=LEVEL
                            Set logging level (INFO|WARN|DEBUG|ERROR)
      -s SYSLOG, --syslog=SYSLOG
                            Log to syslog. Supply facility name. (ie "local0")

The list of paths that you want to monitor are supplied via a YAML
formatted configuration file. Here's an example file:

    /services/foo/min_1:
      children: 1
    /services/foo/min_0:
      children: 0
    /services/foo/min_3:
      children: 3

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
