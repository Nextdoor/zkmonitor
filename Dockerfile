FROM odise/busybox-python:2015.02
MAINTAINER Mikhail Simin <mikhail@nextdoor.com>

RUN mkdir -p /app /app/zk_monitor
ADD runserver.py /app/zk_monitor/runserver.py

EXPOSE 80
ENTRYPOINT ["/app/zk_monitor/runserver.py"]
