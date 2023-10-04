# Slack Logger Python - A Slack Logger for Python Logging

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
![coverage](https://raw.githubusercontent.com/GRBurst/slack-logger-python/assets/badges/coverage.svg)

A python logging implementation to send messages to Slack.
Design goals:
1. Use Python logging interface such that it can be integrated with standard logging tools.
2. Fully customizable messages with full control over message layout and design.
3. Simple authentication via webhook.
4. Powerful filtering to filter e.g. for environments or particular values only known at runtime.
5. Easy usage to cover most use cases when slack is used for basic alerting and automatic traceback visualization.

To achieve aforementioned goals, the library provides logging handler, formatter and filter implementations.

## Getting Started

1. Install with `pip install slack-logger-python`.
2. Now, you can use the `slack_logger` module in your python code.


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
Extra fields are shown in blocks at the bottom of the message and can be dynamically added at runtime.
Everything else stays the same:

```python
from slack_logger import FormatConfig, SlackFormatter, SlackHandler

logger = logging.getLogger(__name__)

format_config = FormatConfig(service="testrunner", environment="test", extra_fields={"foo": "bar"})
formatter = SlackFormatter.default(format_config)
handler = SlackHandler.from_webhook(os.environ["SLACK_WEBHOOK"])
handler.setFormatter(formatter)
handler.setLevel(logging.WARN)

logger.addHandler(handler)

logger.info("I won't appear.")
logger.warning("I will show up.")
logger.error("Mee too.")
```

Adding extra fields on single log message is achieved by just putting it in the extra fields of the logging interface:
```python
logger.warning("I will show up.", extra = {"extra_fields": {"foo": "baba"}})
```

## Customization

To do basic customizations, you can provide a configuration to the `SlackFormatter`:

```python
    service: Optional[str] = None
    environment: Optional[str] = None
    context: List[str] = []
    emojis: Dict[int, str] = DEFAULT_EMOJIS
    extra_fields: Dict[str, str] = {}
```

Let's look at an example error log from a division by zero error.
Given the following code snippet with a configuration and the default formatter:

```python
import os
from slack_logger import FormatConfig, SlackFormatter, SlackHandler
format_config = FormatConfig(
    service="testrunner", environment="test", extra_fields={"foo": "bar", "raven": "caw"}
)
slack_handler = SlackHandler.from_webhook(os.environ["SLACK_WEBHOOK"])
formatter = SlackFormatter.default(format_config)
slack_handler.setFormatter(formatter)
log.addHandler(slack_handler)
try:
    1/0
except Exception:
    log.exception("Something terrible happened!")
```

We will get the following error message in slack:
![error_log](https://raw.githubusercontent.com/GRBurst/slack-logger-python/assets/docs/images/error_log.png)

It contains a header, a context, a body and a section containing extra fields.
Let's identify those in the image above.

The header is composed of:
1. Log level emoji: ❌
2. Log level name: ERROR
3. Service name: testrunner

The context contains:
1. Environment: test
2. Service name: testrunner

The body includes:
1. The log error message: "Something terrible happened!"
2. The Traceback error

Extra fields:
1. Field "foo" with value "bar"
2. Field "raven" with value "caw"

### Design Message - Design Principal (3)

Messages are fully customizable using slacks block layout, see [Creating rich message layouts](https://api.slack.com/messaging/composing/layouts) and [Reference: Layout blocks](https://api.slack.com/reference/block-kit/blocks).
By implementing the `MessageDesign` interface, you can fully control in the message design, which requires you to implement a function `format_blocks(record: LogRecord) -> Sequence[Optional[Block]]` to transform a `LogRecord` into a sequence of slack message blocks.
Of course, you can add configurations and helper functions as well.

Let's create our own warning message.
This demonstrates the usage and the implementation of design goal (2).

```python
import attrs # for convenience, but not required
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


#### Provide your own set of emojis

To the default emoji set is a defined by the following dict:
```python
DEFAULT_EMOJIS = {
    logging.CRITICAL: ":fire:",     # 🔥
    logging.ERROR: ":x:",           # ❌
    logging.FATAL: ":x:",           # ❌
    logging.WARNING: ":warning:",   # ⚠️
    logging.WARN: ":warning:",      # ⚠️
    logging.INFO: ":bell:",         # 🔔
    logging.DEBUG: ":microscope:",  # 🔬 
    logging.NOTSET: ":mega:",       # 📣
}
```

You can import and overwrite it partially - or you can define a complete new set of emoji.
The following example demonstrates how you can add the emoji set to the `SlackFormatter`:

```python
from slack_logger import FormatConfig, SlackFormatter

my_emojis = {
    logging.CRITICAL: ":x:",    # ❌
    logging.ERROR: ":x:",       # ❌
    logging.FATAL: ":x:",       # ❌
    logging.WARNING: ":bell:",  # 🔔
    logging.WARN: ":bell:",     # 🔔
    logging.INFO: ":mega:",     # 📣
    logging.DEBUG: ":mega:",    # 📣
    logging.NOTSET: ":mega:",   # 📣
}

config = FormatConfig(service="testrunner", environment="test", emojis=my_emojis)
formatter = SlackFormatter.default(config)
```


### Filter Message

Filters implement the logging interface of `Filters`.
They are designed to work as a companion to a `LogFormatter`, as it can filter on the formatters config.
A message is logged if a filter is matched successfully.
Design goal (4) and (5) are partially demonstrated.

Here is a quick example:

```python
from slack_logger import FilterConfig, SlackFilter, SlackHandler
import os
import logging 

logger = logging.getLogger("ProdFilter")
# Allow only logs from `prod` environment
filter = SlackFilter(config=FilterConfig(environment="prod"), filterType=FilterType.AnyAllowList)
slack_handler.addFilter(filter)
logger.addHandler(slack_handler)


# When the ENV enviroment variable is set to prod, the message will be send.
# Otherwise, the message is filtered out and not send (e.g. if ENV is `dev`)
logger.warning(f"{log_msg} in some environment and allow listed prod", extra={"filter": {"environment": os.getenv("ENV", "dev")}})

# Will be filtered
logger.warning(f"{log_msg} in dev environment and allow listed prod", extra={"filter": {"environment": "dev"}})

# Will be send
logger.warning(f"{log_msg} in dev environment and allow listed prod", extra={"filter": {"environment": "prod"}})
```

Note that we used the `"filter"` property in the `extra` field option here to inject a config, as we don't use a `SlackFormatter`.
You can think of it as a reserved word.
This `on-the-fly` configurations allow to specify properties on messages to alter the filter behavior for a single log message.

There are 4 different types of filter lists:
- `FilterType.AnyAllowList`: Pass filter if any of the provided conditions are met.
- `FilterType.AllAllowList`: Pass filter only if all provided conditions are met.
- `FilterType.AnyDenyList`: Pass filter if no condition is met and deny if any condition is met.
- `FilterType.AllDenyList`: Pass filter if any condition is met and deny if all conditions are met.

#### Combining multiple filters.

It is important to note that as soon a message does not meet any filter condition, it is filtered out and won't appear in the logs, as it is simply the overlap of all filter conditions.
Therefore it is not possible to allow a denied message afterwards.
Furthermore, the order of filters do not matter.


The composition of configurations, filters and dynamic extra fields allow for a flexible way of specifying your message content and filter unwanted messages.

More examples can be found it the [tests folder](https://github.com/GRBurst/slack-logger-python/tree/main/tests).

