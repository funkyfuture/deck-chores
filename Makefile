.PHONY: clean clean-test clean-pyc clean-build docs help build build-dev run-dev release-arm release-arm release-multiimage
.DEFAULT_GOAL := build-dev

REPO_NAME = funkyfuture/deck-chores
VERSION = $(shell grep __version__ deck_chores/__init__.py | cut -f3 -d" " | tr -d "'")
IMAGE_NAME = $(REPO_NAME):$(VERSION)
SOURCE_COMMIT = $(shell git rev-parse HEAD)
BUILD_DATE = "$(shell date --rfc-3339 seconds)"
BUILD_ARGS = --build-arg BUILD_DATE=$(BUILD_DATE) --build-arg SOURCE_COMMIT=$(SOURCE_COMMIT) --build-arg VERSION=$(VERSION)

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

build: ## builds the Docker image
	docker build $(BUILD_ARGS) -t $(IMAGE_NAME) .

run: build ## runs deck-chores in a temporary container
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock $(IMAGE_NAME)

build-dev: ## builds the Docker image for debugging
	docker build -t $(REPO_NAME):dev --rm -f Dockerfile-dev .

run-dev: build-dev ## runs deck-chores in a temporary container for debugging
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock $(REPO_NAME):dev

clean: clean-build clean-pyc clean-test ## cleans all artifacts

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

test: ## run all tests
	tox

docs: ## generate Sphinx HTML documentation, including API docs
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	xdg-open docs/_build/html/index.html

release: test clean build ## release the current version on github, the PyPI and the Docker hub
	git tag -f $(VERSION)
	git tag -f latest
	git push origin master
	git push -f origin $(VERSION)
	git push -f origin latest
	python setup.py sdist bdist_wheel upload
	$(MAKE) release-multiimage

release-arm: ## release the arm build on the Docker hub
	hooks/release-arm $(IMAGE_NAME) $(SOURCE_COMMIT)

release-multiimage: release-arm ## release the multi-arch manifest on the Docker hub
	hooks/release-multiimage $(REPO_NAME) $(VERSION)

dist: clean ## builds source and wheel package
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

install: clean ## install the package to the active Python's site-packages
	python setup.py install
