.DEFAULT_GOAL := build-dev

REPO_NAME = funkyfuture/deck-chores
VERSION = $(shell poetry version --short)
IMAGE_NAME = $(REPO_NAME):$(VERSION)

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

.PHONY: black
black: ## code-formatting with black
	poetry run black deck_chores tests

.PHONY: build
build: ## builds the Docker image
	docker build --tag $(IMAGE_NAME) .

.PHONY: build-dev
build-dev: ## builds the Docker image for debugging
	docker build -t $(REPO_NAME):dev --rm -f Dockerfile-dev .

.PHONY: clean
clean: clean-build clean-pyc clean-test ## cleans all artifacts
	$(MAKE) -C docs clean

.PHONY: clean-build
clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	rm -fr deck_chores.egg-info/
	rm -fr pip-wheel-metadata/

.PHONY: clean-pyc
clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

.PHONY: clean-test
clean-test: ## remove test and coverage artifacts
	rm -fr .cache/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .mypy_cache/
	rm -fr .pytest_cache/

.PHONY: docs
docs: ## generate Sphinx HTML documentation, including API docs
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	xdg-open docs/_build/html/index.html

.PHONY: doclinks
docslinks: ## checks the referenced URLs in the docs
	$(MAKE) -C docs linkchecks

.PHONY: help
help: ## print make targets help
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

.PHONY: lint
lint: black ## check style with flake8
	poetry run flake8 --max-complexity=10 --max-line-length=89 deck_chores tests

.PHONY: mypy
mypy:  ## check types with mypy
	poetry run mypy --ignore-missing-imports deck_chores

.PHONY: pytest
pytest: ## run tests with pytest
	poetry run pytest --cov=deck_chores --cov-report term-missing --cov-fail-under 90

.PHONY: test
test: lint mypy pytest ## run all tests

.PHONY: release
release: test doclinks build ## release the current version on github, the PyPI and the Docker hub
	git tag $(VERSION)
	git push origin refs/tags/$(VERSION)

.PHONY: run
run: build ## runs deck-chores in a temporary container
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock $(IMAGE_NAME)

.PHONY: run-dev
run-dev: build-dev ## runs deck-chores in a temporary container for debugging
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock $(REPO_NAME):dev
