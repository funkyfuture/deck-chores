.PHONY: clean clean-test clean-pyc clean-build docs help build build-dev tag_latest run-dev
.DEFAULT_GOAL := build-dev

NAME = funkyfuture/deck-chores
VERSION = 0.1
BUILD_DATE = $(shell date --rfc-3339=seconds)
COMMIT = 'None'
# FIXME COMMIT = $(shell git rev-parse HEAD)

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BUILD_ARGS = --build-arg BUILD_DATE="$(BUILD_DATE)" --build-arg COMMIT=$(COMMIT) --build-arg VERSION=$(VERSION)

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

all: build

build:
	docker build -t $(NAME):$(VERSION) $(BUILD_ARGS) --rm .

run:
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock $(NAME):$(VERSION)

build-dev:
	docker build -t $(NAME):dev --rm -f Dockerfile-dev .

run-dev:
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock $(NAME):dev

clean: clean-build clean-pyc clean-test


clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

lint: ## check style with flake8
	flake8 deck_chores tests

test: ## run tests
	TODO

docs: ## generate Sphinx HTML documentation, including API docs
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	xdg-open docs/_build/html/index.html

tag_latest:
	docker tag -f $(NAME):$(VERSION) $(NAME):latest

release: clean build tag_latest
	python setup.py sdist upload
	python setup.py bdist_wheel upload
	docker push $(NAME)

dist: clean ## builds source and wheel package
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

install: clean ## install the package to the active Python's site-packages
	python setup.py install
