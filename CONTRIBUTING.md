# Contributing

Contributions are very welcome.
Please file issues or submit pull requests in our [GitHub repository][repo].
All contributors will be acknowledged,
but must abide by our Code of Conduct.

## Setup

-   `uv venv` (once)
-   `source .venv/bin/activate`
-   `uv sync --extra dev`

## Operations

`make` with no arguments displays a list of actions:

| target    | action |
| :-------- | :----- |
| commands  | show available commands (*) |
| benchmark | run benchmark for N=10000 |
| build     | build package |
| check     | check code issues |
| clean     | clean up |
| coverage  | run tests with coverage |
| docs      | build documentation |
| fix       | fix code issues |
| format    | format code |
| lint      | run all code checks |
| examples  | regenerate example output |
| publish   | publish using ~/.pypirc credentials |
| scenarios | regenerate scenario output |
| serve     | serve documentation |
| test      | run tests |
| types     | check types |

[repo]: https://github.com/gvwilson/asimpy
