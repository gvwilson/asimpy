.PHONY: docs
all: commands

EXAMPLE_SRC:=$(filter-out examples/__init__.py examples/_util.py,$(wildcard examples/*.py))
EXAMPLE_OUT:=$(patsubst examples/%.py,output/%.txt,${EXAMPLE_SRC})

## commands: show available commands (*)
commands:
	@grep -h -E '^##' ${MAKEFILE_LIST} \
	| sed -e 's/## //g' \
	| column -t -s ':'

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
docs: ${EXAMPLE_OUT}
	@find . -path './.venv' -prune -o -type f -name '*~' -exec rm {} +
	@zensical build --clean
	@touch docs/.nojekyll

## examples: re-run all examples
examples: ${EXAMPLE_OUT}

output/%.txt: examples/%.py
	@mkdir -p output
	python $< > $@

## fix: fix code issues
fix:
	@ruff check --fix .

## format: format code
format:
	@ruff format .

## package: build package
package:
	@python -m build

## publish: publish using ~/.pypirc credentials
publish:
	@twine upload --verbose dist/*

## test: run tests
test:
	@pytest tests
