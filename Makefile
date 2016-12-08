.PHONY: clean clean-test clean-pyc clean-build docs help build build-dev run-dev
.DEFAULT_GOAL := build-dev

NAME = funkyfuture/deck-chores
VERSION = $(shell grep __version__ deck_chores/__init__.py | cut -f3 -d" ")

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

all: build

build:
	docker build -t $(NAME):$(VERSION) --rm .

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

test:
	tox

docs: ## generate Sphinx HTML documentation, including API docs
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	xdg-open docs/_build/html/index.html

release: test clean build
	git tag -f latest
	git push
	git push --tags
	python setup.py sdist bdist_wheel upload

dist: clean ## builds source and wheel package
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

install: clean ## install the package to the active Python's site-packages
	python setup.py install
