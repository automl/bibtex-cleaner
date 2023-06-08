# These have been configured to only really run short tasks. Longer form tasks
# are usually completed in github actions.

NAME := bibtex-cleaner
PACKAGE_NAME := bibtex-cleaner

DIR := "${CURDIR}"
SOURCE_DIR := ${PACKAGE_NAME}
.PHONY: help install-dev check format clean help:
	@echo "Makefile ${NAME}"
	@echo "* install-dev      to install all dev requirements and install pre-commit"
	@echo "* clean            to clean any doc or build files"
	@echo "* check            to check the source code for issues"
	@echo "* format           to format the code with black and isort"
	PYTHON ?= python
PIP ?= python -m pip
MAKE ?= make
BLACK ?= black
ISORT ?= isort
PYDOCSTYLE ?= pydocstyle
MYPY ?= mypy
FLAKE8 ?= flake8

install-dev:
	$(PIP) install -e ".[dev]"
	check-black:
	$(BLACK) ${SOURCE_DIR} --check || :
	check-isort:
	$(ISORT) ${SOURCE_DIR} --check || :

check-pydocstyle:
	$(PYDOCSTYLE) ${SOURCE_DIR} || :

check-mypy:
	$(MYPY) ${SOURCE_DIR} || :

check-flake8:
	$(FLAKE8) ${SOURCE_DIR} || :
	$(FLAKE8) ${TESTS_DIR} || :

check: check-black check-isort check-mypy check-flake8 check-pydocstyle

format-black:
	$(BLACK) ${SOURCE_DIR}
	format-isort:
	$(ISORT) ${SOURCE_DIR}

format: format-black format-isort

# Clean up any builds in ./dist as well as doc, if present
clean: 