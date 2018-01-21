.DEFAULT_GOAL := build-dev

REPO_NAME = funkyfuture/deck-chores
VERSION = $(shell git describe --tags)
IMAGE_NAME = $(REPO_NAME):$(VERSION)
GIT_SHA1 = $(shell git rev-parse HEAD)

export IMAGE_NAME
export GIT_SHA1

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

.PHONY: help
help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

.PHONY: build
build: ## builds the Docker image
	hooks/build

.PHONY: run
run: build ## runs deck-chores in a temporary container
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock $(IMAGE_NAME)

.PHONY: build-dev
build-dev: ## builds the Docker image for debugging
	docker build -t $(REPO_NAME):dev --rm -f Dockerfile-dev .

.PHONY: run-dev
run-dev: build-dev ## runs deck-chores in a temporary container for debugging
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock $(REPO_NAME):dev

.PHONY: clean
clean: clean-build clean-pyc clean-test ## cleans all artifacts

.PHONY: clean-build
clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

.PHONY: clean-pyc
clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

.PHONY: clean-test
clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

.PHONY: lint
lint: ## check style with flake8
	flake8 deck_chores tests

.PHONY: test
test: ## run all tests
	tox

.PHONY: docs
docs: ## generate Sphinx HTML documentation, including API docs
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	xdg-open docs/_build/html/index.html

.PHONY: release
release: test clean build ## release the current version on github, the PyPI and the Docker hub
	git tag -f $(VERSION)
	git push origin master
	git push -f origin $(VERSION)
	python setup.py sdist bdist_wheel upload
	$(MAKE) release-multiimage

.PHONY: release-arm
release-arm: ## release the arm build on the Docker hub
	hooks/release-arm $(IMAGE_NAME) $(GIT_SHA1)

.PHONY: release-multiimage
release-multiimage: release-arm ## release the multi-arch manifest on the Docker hub
	hooks/release-multiimage $(REPO_NAME) $(VERSION)

.PHONY: dist
dist: clean ## builds source and wheel package
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

.PHONY: install
install: clean ## install the package to the active Python's site-packages
	python setup.py install
