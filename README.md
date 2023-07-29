# Slack Python Logger

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
![coverage](https://raw.githubusercontent.com/GRBurst/slack-logger-python/assets/badges/coverage.svg)

A python logging implementation to send messages to Slack.
Design goals:
1. Python logging interface to be used with the standard logging tools
2. Fully customizable messages with full control over message layout and design.
3. Simple authentication via webhook.
4. Powerful filtering to filter e.g. for environments or particular values only known at runtime.
5. Easy usage to cover most use cases when slack is used for basic alerting.

To achive aforementioned goals, a handler and a formatter is provided.

## Getting Started

1. Install with `pip install slack-logger-python`.
2. Now, you can use the `slack_logger` logger in your python code.


### Basic Example with Plain Messages

This basic examples shows the usage and the implementation of design goal (1) and (3).

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


## Design Message - Design Principal (3)

Messages are fully customizable using slacks block layout, see [Creating rich message layouts](https://api.slack.com/messaging/composing/layouts) and [Reference: Layout blocks](https://api.slack.com/reference/block-kit/blocks).
By implementing the `MessageDesign` interface, you can fully control in the message design.
This demonstrates the usage and the implementation of design goal (2).
Let's create our own warning message:

```python
import attrs # for convenience, but required
from slack_sdk.models.blocks import Block, DividerBlock, HeaderBlock, SectionBlock
from slack_logger import SlackFormatter

@define
class CustomDesign(MessageDesign):

    def format_blocks(self, record: LogRecord) -> Sequence[Optional[Block]]:
        level = record.levelname
        message = record.getMessage()

        blocks: Sequence[Block] = [
            HeaderBlock(text=PlainTextObject(text=f"{level} {message}")),
            DividerBlock(),
            SectionBlock(text=MarkdownTextObject(text=message)),
        ]
        return blocks

formatter = SlackFormatter(design=CustomDesign())
```


### Provide your own set of emojis

To the default formatter:

```python
from slack_logger import Configuration, SlackFormatter

my_emojis = {
    logging.CRITICAL: ":x:",
    logging.ERROR: ":x:",
    logging.FATAL: ":x:",
    logging.WARNING: ":bell:",
    logging.WARN: ":bell:",
    logging.INFO: ":mega:",
    logging.DEBUG: ":mega:",
    logging.NOTSET: ":mega:",
}

config = Configuration(service="testrunner", environment="test", emojis=my_emojis)
formatter = SlackFormatter.default(config)
```


## Filter Message

Filters implement the logging interface of `Filters`.
Design goal (4) and (5) are partially demonstrated.

```python
from slack_logger import Configuration, SlackFilter, SlackHandler
import os
import logging 

logger = logging.getLogger("ProdFilter")
# Allow only logs from `prod` environment
filter = SlackFilter(config=Configuration(environment="prod"), filterType=FilterType.AnyWhitelist)
slack_handler.addFilter(filter)
logger.addHandler(slack_handler)


# When the ENV enviroment variable is set to prod, the message will be send.
# Otherwise, the message is filtered out and not send (e.g. if ENV is `dev`)
logger.warning(f"{log_msg} in some environment and whitelisted prod", extra={"filter": {"environment": os.getenv("ENV", "dev")}})

# Will be filtered
logger.warning(f"{log_msg} in dev environment and whitelisted prod", extra={"filter": {"environment": "dev"}})

# Will be send
logger.warning(f"{log_msg} in dev environment and whitelisted prod", extra={"filter": {"environment": "prod"}})
```
