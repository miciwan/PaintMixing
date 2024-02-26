SHELL := /bin/bash -eo pipefail

.PHONY: help
help: ## Display this help
	@sed \
		-e '/^[a-zA-Z0-9_\-]*:.*##/!d' \
		-e 's/:.*##\s*/:/' \
		-e 's/^\(.\+\):\(.*\)/$(shell tput setaf 6)\1$(shell tput sgr0):\2/' \
		$(MAKEFILE_LIST) | column -c2 -t -s :

.PHONY: targets
targets: help ## Display this help

.PHONY: list
list: help ## Display this help

.PHONY: pipenv lint deadcode typing format-check test coverage clean
pipenv: ## installs all python packages
	pipenv install --dev
lint: ## performs linting for python tooling
	pipenv run flake8 .
deadcode: ## checks for unused code in python tooling
	pipenv run vulture .
typing: ## runs static type checking on python tooling
	pipenv run mypy --install-types --non-interactive .
	pipenv run mypy .
format-check: ## checks formatting on python tooling
	pipenv run black --check --diff .
test: ## runs pytest
	pipenv run coverage run -m pytest -v .
coverage: test ## generates markdown report of pytest coverage
	pipenv run coverage report -m --format markdown
clean:
	rm *.tgz
all: lint deadcode typing format-check coverage ## applies all python checks
