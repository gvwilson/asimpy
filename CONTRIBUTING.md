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

`task --list` displays a list of actions:

| action   | effect |
| -------- | |
| build    | build package |
| check    | check code issues |
| clean    | clean up |
| concat   | concatenate files |
| docs     | build documentation |
| fix      | fix code issues |
| format   | format code |
| lint     | run all code checks |
| examples | regenerate example output |
| publish  | publish using ~/.pypirc credentials |
| serve    | serve documentation |
| types    | check types |

[repo]: https://github.com/gvwilson/asimpy
