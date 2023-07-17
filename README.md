# Slack Python Logging
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Linting: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Slack logger implementing the python logging interface to be used with the standard logging tools in python.

A handler and a formatter is provided, currently working with a webhook url only.

Messages are fully customizable using slacks block layout, see [Creating rich message layouts](https://api.slack.com/messaging/composing/layouts) and [Reference: Layout blocks](https://api.slack.com/reference/block-kit/blocks).

Ment as an logger post messages to slack.
