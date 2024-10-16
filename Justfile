default: build-dev

repo-name := "funkyfuture/deck-chores"
version := "$(pipx run poetry version --short)"
image-name := "{{repo-name}}:{{version}}"


# code-formatting with black
black:
    pipx run black deck_chores tests

# builds the Docker image
build:
	docker build --tag {{image-name}} .

# builds the Docker image for debugging
build-dev:
	docker build -t {{repo-name}}:dev --rm -f Dockerfile-dev .

# cleans all artifacts
clean: clean-build clean-pyc clean-test
	make -C docs clean

# remove build artifacts
clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	rm -fr deck_chores.egg-info/
	rm -fr pip-wheel-metadata/

# remove Python file artifacts
clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

# remove test and coverage artifacts
clean-test:
	rm -fr .cache/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .mypy_cache/
	rm -fr .pytest_cache/

# generate Sphinx HTML documentation, including API docs
docs:
	make -C docs clean
	make -C docs html
	xdg-open docs/_build/html/index.html

# checks the referenced URLs in the docs
docslinks:
	make -C docs linkcheck

# check style with flake8
lint: black
	pipx run flake8 --max-complexity=10 --max-line-length=89 deck_chores tests

# check types with mypy
mypy:
	pipx run poetry run mypy --ignore-missing-imports deck_chores

# run tests with pytest
pytest:
	pipx run poetry run pytest --cov=deck_chores --cov-report term-missing --cov-fail-under 90

# release the current version on github, the PyPI and the Docker hub
release: test docslinks build
	git tag {{version}}
	git push origin refs/tags/{{version}}

# runs deck-chores in a temporary container
run: build
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock {{image-name}}

# runs deck-chores in a temporary container for debugging
run-dev: build-dev
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock {{repo-name}}:dev

# run all tests
test: lint mypy pytest
