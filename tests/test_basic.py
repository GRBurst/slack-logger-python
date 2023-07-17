import logging
import os

import pytest

from slack_logger import Configuration, SlackFormatter, SlackHandler

logger = logging.getLogger("LocalTest")
config = Configuration(service="testrunner", environment="test", fields={"foo": "bar"})

log_format_str = "%(asctime)s %(name)s|%(levelname)s: %(message)s"
log_formatter = logging.Formatter(log_format_str)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_formatter)


def basic_logging() -> int:
    # formatter = SlackFormatter.plain()
    # formatter = SlackFormatter.minimal(config)
    formatter = SlackFormatter.default(config)
    handler = SlackHandler.from_webhook(os.environ["SLACK_WEBHOOK"])
    handler.setFormatter(formatter)
    handler.setLevel(logging.WARN)

    stream_handler.setLevel(logging.WARN)

    logger.addHandler(stream_handler)
    logger.addHandler(handler)

    print("logging")
    logger.info("Foo bar haha")
    logger.warning("oO warning")
    logger.error("something broke")

    return 0


def exception_logging() -> None:
    formatter = SlackFormatter.default(config)
    handler = SlackHandler.from_webhook(os.environ["SLACK_WEBHOOK"])
    handler.setFormatter(formatter)
    handler.setLevel(logging.WARN)

    stream_handler.setLevel(logging.WARN)

    logger.addHandler(stream_handler)
    logger.addHandler(handler)

    try:
        1 / 0
    except Exception as e:
        logger.error("Error!", exc_info=e)
        raise e


def auto_exception_logging() -> int:
    formatter = SlackFormatter.default(config)
    handler = SlackHandler.from_webhook(os.environ["SLACK_WEBHOOK"])
    handler.setFormatter(formatter)
    handler.setLevel(logging.WARN)

    stream_handler.setLevel(logging.WARN)

    logger.addHandler(stream_handler)
    logger.addHandler(handler)

    try:
        1 / 0
    except Exception as e:
        logger.exception("Exception!")
        raise e

    return 0


class TestBasicLogging:
    def test_basic_logging(self) -> None:
        assert basic_logging() == 0

    def test_exception_logging(self) -> None:
        with pytest.raises(Exception) as exc_info:
            exception_logging()

    def test_auto_exception_logging(self) -> None:
        with pytest.raises(Exception) as exc_info:
            auto_exception_logging()
