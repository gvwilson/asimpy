.PHONY: docs
all: commands

## commands: show available commands (*)
commands:
	@grep -h -E '^##' ${MAKEFILE_LIST} \
	| sed -e 's/## //g' \
	| column -t -s ':'

## build: build package
build:
	@python -m build

## check: check code issues
check:
	@ruff check .
	@ty check src

## clean: clean up
clean:
	@rm -rf ./dist
	@find . -path './.venv' -prune -o -type d -name '__pycache__' -exec rm -rf {} +
	@find . -path './.venv' -prune -o -type f -name '*~' -exec rm {} +

## coverage: run tests with coverage
coverage:
	@python -m coverage run -m pytest tests
	@python -m coverage report --show-missing

.PHONY: docs
## docs: make documentation
docs:
	@zensical build --clean
	@touch docs/.nojekyll

## fix: fix code issues
fix:
	@ruff check --fix .

## format: format code
format:
	@ruff format .

## publish: publish using ~/.pypirc credentials
publish:
	@twine upload --verbose dist/*

## test: run tests
test:
	@pytest tests
