include Makefile.docker  # Docker related. No app-related commands there.

HERE = $(shell pwd)
BIN = $(HERE)/bin

TAG = zkmonitor

BUILD_DIRS = bin build include lib lib64 man share

ZOOKEEPER = $(BIN)/zookeeper
ZOOKEEPER_VERSION ?= 3.4.6
ZOOKEEPER_PATH ?= $(ZOOKEEPER)
ZOOKEEPER_URL = http://apache.osuosl.org/zookeeper/zookeeper-$(ZOOKEEPER_VERSION)/zookeeper-$(ZOOKEEPER_VERSION).tar.gz

.PHONY: all build clean test zookeeper clean-zookeeper

all: build

build: .build

.build: setup.py requirements.txt requirements.test.txt
	python setup.py install
	pip install -r requirements.test.txt
	touch .build

image:
	docker build -t $(TAG) .

run:
	docker rm -f $(TAG) || echo 'Nothing is running.'
	docker run --name "$(TAG)" $(TAG)

clean:
	rm -rf $(BUILD_DIRS)
	rm .build

test: build
	python setup.py test pep8 pyflakes

integration: build $(ZOOKEEPER)
	PYFLAKES_NODOCTEST=True ZOOKEEPER_PATH=$(ZOOKEEPER_PATH) python setup.py integration pep8 pyflakes

$(ZOOKEEPER):
	@echo "Installing Zookeeper"
	mkdir -p $(BIN) && cd $(BIN) && curl -C - $(ZOOKEEPER_URL) | tar -zx
	mv $(BIN)/zookeeper-$(ZOOKEEPER_VERSION) $(ZOOKEEPER_PATH)
	chmod a+x $(ZOOKEEPER_PATH)/bin/zkServer.sh
	cp $(ZOOKEEPER_PATH)/conf/zoo_sample.cfg $(ZOOKEEPER_PATH)/conf/zoo.cfg
	@echo "Finished installing Zookeeper"

zookeeper: $(ZOOKEEPER)
	$(ZOOKEEPER_PATH)/bin/zkServer.sh start

clean-zookeeper:
	rm -rf zookeeper $(ZOOKEEPER_PATH)
