.PHONY: config install lint full-lint mypy test build publish clean all ci
.DEFAULT_GOAL := all

all: install lint mypy test build
ci: all

VIRTUAL_ENV = .venv
BIN = .venv/bin/
PYTHON = `pyenv which python`
POETRY_VERSION = 1.0.3
PIP_VERSION = 20.0.2

PROJECT = market-maker
PACKAGE = csv_import
TAG ?= latest
DEV ?= 1

config:
	${BIN}poetry config virtualenvs.in-project true
	${BIN}poetry config repositories.b9prime "${PYPI_URL}"
	${BIN}poetry config virtualenvs.create `if [ "${DEV}" = "0" ]; then echo false; else echo true; fi`
	mkdir -p ~/.config/pypoetry/ | true
	echo "[http-basic]" > ~/.config/pypoetry/auth.toml
	echo "[http-basic.b9prime]" >> ~/.config/pypoetry/auth.toml
	echo "username = \"${PYPI_USER}\"" >> ~/.config/pypoetry/auth.toml
	echo "password = \"${PYPI_PASSWORD}\"" >> ~/.config/pypoetry/auth.toml

prepare:
	if [ "${DEV}" = "1" ]; then ${PYTHON} -m venv ${VIRTUAL_ENV}; fi
	${BIN}pip install pip==${PIP_VERSION}
	${BIN}pip install poetry==${POETRY_VERSION}

install:
	make prepare
	make config
	${BIN}poetry install -v `if [ "${DEV}" = "0" ]; then echo "--no-dev --no-interaction --no-ansi"; fi`
	${BIN}pip uninstall -y typing asyncio

lint:
	${BIN}isort --recursive src tests
	${BIN}flake8 --max-line-length=140 src tests || true

full-lint:
	${BIN}isort --recursive src tests
	${BIN}pylint src tests || poetry run pylint-exit $$?

mypy:
	${BIN}mypy src tests

test:
	${BIN}nosetests -v --with-coverage tests --cover-package $(PACKAGE)

build:
	${BIN}poetry build

publish:
	make prepare
	make config
	${BIN}poetry publish --build -r b9prime

clean:
	rm -rf build dist
