EXAMPLES_SRC=$(wildcard examples/*.py)
EXAMPLES_OUT=$(patsubst examples/%.py,output/examples/%.txt,${EXAMPLES_SRC})
SCENARIOS_SRC=$(wildcard scenarios/*.py)
SCENARIOS_OUT=$(patsubst scenarios/%.py,output/scenarios/%.txt,${SCENARIOS_SRC})

.PHONY: docs
all: commands

## commands: show available commands (*)
commands:
	@grep -h -E '^##' ${MAKEFILE_LIST} \
	| sed -e 's/## //g' \
	| column -t -s ':'

## benchmark: run benchmark for N=10000
benchmark:
	python benchmark/benchmark.py 10000

## build: build package
build:
	python -m build

## check: check code issues
check:
	@ruff check .

## clean: clean up
clean:
	@rm -rf ./dist
	@find . -path './.venv' -prune -o -type d -name '__pycache__' -exec rm -rf {} +
	@find . -path './.venv' -prune -o -type f -name '*~' -exec rm {} +

## coverage: run tests with coverage
coverage:
	@python -m coverage run -m pytest tests
	@python -m coverage report --show-missing

## docs: build documentation
docs:
	@mkdocs build
	@touch docs/.nojekyll
	@cp docs-requirements.txt docs/requirements.txt

## fix: fix code issues
fix:
	ruff check --fix .

## format: format code
format:
	ruff format .

## lint: run all code checks
lint:
	@make check
	@make types

## examples: regenerate example output
examples: ${EXAMPLES_OUT}

output/examples/%.txt: examples/%.py
	@mkdir -p output/examples
	python $< > $@ 2>&1

## publish: publish using ~/.pypirc credentials
publish:
	twine upload --verbose dist/*

## scenarios: regenerate scenario output
scenarios: ${SCENARIOS_OUT}

output/scenarios/%.txt: scenarios/%.py
	@mkdir -p output/scenarios
	python $< > $@ 2>&1

## serve: serve documentation
serve:
	python -m http.server -d docs

## test: run tests
test:
	pytest tests

## types: check types
types:
	ty check .
