# Slack Python Logging
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

Slack logger implementing the python logging interface to be used with the standard logging tools in python.

A handler and a formatter is provided, currently working with a webhook url only.

Messages are fully customizable using slacks block layout, see [Creating rich message layouts](https://api.slack.com/messaging/composing/layouts) and [Reference: Layout blocks](https://api.slack.com/reference/block-kit/blocks).

Ment as an logger post messages to slack.

## Getting Started

1. Install with `pip install slack-logger-python`.
2. Now, you can use the `slack_logger` logger in your python code.


### Basic Example with Plain Messages

```python
from slack_logger import SlackFormatter, SlackHandler

logger = logging.getLogger(__name__)

formatter = SlackFormatter.plain() # plain message, no decorations
handler = SlackHandler.from_webhook(os.environ["SLACK_WEBHOOK"])
handler.setFormatter(formatter)
handler.setLevel(logging.WARN)

logger.addHandler(handler)

logger.info("I won't appear.")
logger.warning("I will show up.")
logger.error("Mee too.")
```

### Visually Appealing Messages

You can use the `SlackFormatter.minimal()` and `SlackFormatter.default()` formatter for more visually appealing log messages.
For now, those require a configuration to show e.g. the header.
Everything else stays the same:

```python
from slack_logger import Configuration, SlackFormatter, SlackHandler

logger = logging.getLogger(__name__)

config = Configuration(service="testrunner", environment="test", extra_fields={"foo": "bar"})
formatter = SlackFormatter.default(config)
handler = SlackHandler.from_webhook(os.environ["SLACK_WEBHOOK"])
handler.setFormatter(formatter)
handler.setLevel(logging.WARN)

logger.addHandler(handler)

logger.info("I won't appear.")
logger.warning("I will show up.")
logger.error("Mee too.")
```
