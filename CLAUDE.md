# asimpy

This project is a simple, efficient framework for discrete event
simulation in Python using async/await instead of yield. Its
inspiration is Python's [simpy][simpy] library, which is efficient and
has a relatively simple API, but which uses yield instead of
async/await.

## Build and Test Commands

-   Repeatable actions are saved in `Makefile`.
    -   Run `make` with no arguments to get an up-to-date list of targets.
-   `make check` runs checks on the code.
-   `make test` uses `pytest` to run all tests.
-   `make docs` rebuilds the documentation from the Markdown files.

## Style Rules

-   Examples are written as terse prose.
-   Do not use **bold** or *italics* in prose.
-   Do not attempt to be funny or offer generic positive feedback to readers.
-   Do not over-use semi-colons or em-dashes.

[simpy]: https://simpy.readthedocs.io/
