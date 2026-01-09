# Contributing

Contributions are very welcome.
Please file issues or submit pull requests in our [GitHub repository][repo].
All contributors will be acknowledged,
but must abide by our [Code of Conduct](./CODE_OF_CONDUCT.md).

-   Setup:
    -   `uv venv` (once)
    -   `source .venv/bin/activate`
    -   `uv sync --extra dev`
-   Check package: `make check`
-   Build package: `make build`
-   Publish package: `twine upload --verbose -u __token__ -p your-pypi-access-token dist/*`
-   Build documentation: `make docs`

[repo]: https://github.com/gvwilson/asimpy
