.PHONY: config install lint full-lint mypy test build publish clean all ci
.DEFAULT_GOAL := all

all: install lint mypy test build
ci: all

VIRTUAL_ENV = .venv
BIN = .venv/bin/
PYTHON = `python`
POETRY_VERSION = 1.0.3
PIP_VERSION = 20.0.2

PROJECT = csv-import
PACKAGE = csv_import
TAG ?= latest
DEV ?= 1

config:
	poetry config virtualenvs.create `if [ "${DEV}" = "0" ]; then echo false; else echo true; fi`
	mkdir -p ~/.config/pypoetry/ | true

prepare:
	pip install pip==${PIP_VERSION}
	pip install poetry==${POETRY_VERSION}

install:
	make prepare
	make config
	poetry install -v `if [ "${DEV}" = "0" ]; then echo "--no-dev --no-interaction --no-ansi"; fi`
	pip uninstall -y typing asyncio

lint:
	poetry run isort --recursive src tests
	poetry run flake8 --max-line-length=140 src tests || true

full-lint:
	poetry run isort --recursive src tests
	poetry run pylint src tests || poetry run pylint-exit $$?

mypy:
	poetry run mypy src tests

test:
	poetry run nosetests -v --with-coverage tests --cover-package $(PACKAGE)

build:
	poetry build

publish:
	make prepare
	make config
	poetry publish --build

clean:
	rm -rf build dist
