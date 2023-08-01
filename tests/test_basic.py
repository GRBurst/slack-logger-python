import logging
from typing import Dict, Generator

import pytest

from slack_logger import FormatConfig, SlackFormatter, SlackHandler

from .utils import DEFAULT_ADDITIONAL_FIELDS, default_msg, minimal_msg, plain_msg, text_msg

logger = logging.getLogger("BasicTests")

# Setup test handler
slack_handler = SlackHandler.dummy()
slack_handler.setLevel(logging.WARN)
logger.addHandler(slack_handler)

# Different variants of logging are tested.
# We use the caplog fixture, which captures all log messages when running a test.
# The caplog can then be compared to the expected log messages.
# The signature of the tests function is ignore because of caplog fixtures,
# which does not play nicely with mypy.


@pytest.fixture(autouse=True)
def cleanup(caplog) -> Generator:  # type: ignore
    caplog.clear()
    slack_handler.setFormatter(None)
    slack_handler.filters = []
    yield slack_handler
    slack_handler.setFormatter(None)
    slack_handler.filters = []
    caplog.clear()


def test_basic_unformatted_logging(caplog) -> None:  # type: ignore
    """Check if only correct level is logged when not using a SlackFormatter"""
    log_msg = "from basic_text_logging"

    logger.info(f"unformatted info {log_msg}")
    logger.warning(f"unformatted warning {log_msg}")
    logger.error(f"unformatted error {log_msg}")

    assert text_msg(f"unformatted info {log_msg}") not in caplog.messages
    assert text_msg(f"unformatted warning {log_msg}") in caplog.messages
    assert text_msg(f"unformatted error {log_msg}") in caplog.messages


def test_basic_plain_formatted_logging(caplog) -> None:  # type: ignore
    """Check if only correct level is logged when not using plain SlackFormatter"""
    log_msg = "from basic_text_logging"
    formatter = SlackFormatter.plain()
    slack_handler.setFormatter(formatter)

    logger.info(f"plain info {log_msg}")
    logger.warning(f"plain warning {log_msg}")
    logger.error(f"plain error {log_msg}")

    assert plain_msg(f"plain info {log_msg}") not in caplog.messages
    assert plain_msg(f"plain warning {log_msg}") in caplog.messages
    assert plain_msg(f"plain error {log_msg}") in caplog.messages


def test_basic_minimal_formatted_logging(caplog) -> None:  # type: ignore
    """Check if only correct level is logged when not using minimal SlackFormatter"""
    log_msg = "from basic_text_logging"
    minimal_config = FormatConfig(service="testrunner", environment="test")
    formatter = SlackFormatter.minimal(minimal_config)
    slack_handler.setFormatter(formatter)

    logger.info(f"minimal info {log_msg}")
    logger.warning(f"minimal warning {log_msg}")
    logger.error(f"minimal error {log_msg}")

    assert minimal_msg(f"minimal info {log_msg}", levelno=logging.INFO) not in caplog.messages
    assert minimal_msg(f"minimal warning {log_msg}", levelno=logging.WARNING) in caplog.messages
    assert minimal_msg(f"minimal error {log_msg}", levelno=logging.ERROR) in caplog.messages


def test_basic_default_formatted_logging(caplog) -> None:  # type: ignore
    """Check if only correct level is logged when not using default SlackFormatter"""
    log_msg = "from basic_text_logging"
    service_config = FormatConfig(service="testrunner", environment="test", extra_fields={"foo": "bar", "raven": "caw"})
    formatter = SlackFormatter.default(service_config)
    slack_handler.setFormatter(formatter)

    logger.info(f"default info {log_msg}")
    logger.warning(f"default warning {log_msg}")
    logger.error(f"default error {log_msg}")

    assert default_msg(f"default info {log_msg}", levelno=logging.INFO) not in caplog.messages
    assert default_msg(f"default warning {log_msg}", levelno=logging.WARNING) in caplog.messages
    assert default_msg(f"default error {log_msg}", levelno=logging.ERROR) in caplog.messages


# Logging with extra fields
def test_dynamic_fields_additional(caplog) -> None:  # type: ignore
    """Test if adding extra fields to when creating log messages works"""
    log_msg = "from test_dynamic_fields"
    service_config = FormatConfig(service="testrunner", environment="test", extra_fields={"foo": "bar", "raven": "caw"})
    formatter = SlackFormatter.default(service_config)
    slack_handler.setFormatter(formatter)
    logger.warning(f"additional {log_msg}", extra={"extra_fields": {"cow": "moo"}})

    fields_a: Dict[str, Dict[str, str]] = DEFAULT_ADDITIONAL_FIELDS.copy()
    fields_a.update({"cow": {"text": "*cow*\nmoo", "type": "mrkdwn"}})
    assert (
        default_msg(f"additional {log_msg}", levelno=logging.WARNING, additional_fields_dict=fields_a)
        in caplog.messages
    )


def test_dynamic_fields_overwrite(caplog) -> None:  # type: ignore
    """Test if overwriting extra fields to when creating log messages works"""
    log_msg = "from test_dynamic_fields"
    service_config = FormatConfig(service="testrunner", environment="test", extra_fields={"foo": "bar", "raven": "caw"})
    formatter = SlackFormatter.default(service_config)
    slack_handler.setFormatter(formatter)

    logger.error(f"overwrite {log_msg}", extra={"extra_fields": {"foo": "baba"}})

    fields_o: Dict[str, Dict[str, str]] = DEFAULT_ADDITIONAL_FIELDS.copy()
    fields_o.update({"foo": {"text": "*foo*\nbaba", "type": "mrkdwn"}})
    assert (
        default_msg(f"overwrite {log_msg}", levelno=logging.ERROR, additional_fields_dict=fields_o) in caplog.messages
    )


def test_exception_logging(caplog) -> None:  # type: ignore
    """Test if the stacktrace is extracted correctly when providing exc_info to log.error"""
    log_msg = "Error!"
    service_config = FormatConfig(service="testrunner", environment="test", extra_fields={"foo": "bar", "raven": "caw"})
    formatter = SlackFormatter.default(service_config)
    slack_handler.setFormatter(formatter)

    with pytest.raises(ZeroDivisionError):
        try:
            1 / 0
        except Exception as e:
            logger.error(log_msg, exc_info=e)
            raise

    blocks_prefix = '{"blocks": [{"text": {"text": ":x: ERROR | testrunner", "type": "plain_text"}, "type": "header"}, {"elements": [{"text": ":point_right: test, testrunner", "type": "mrkdwn"}], "type": "context"}, {"type": "divider"}, {"text": {"text": "Error!", "type": "mrkdwn"}, "type": "section"}, {"text": {"text": "```Traceback (most recent call last):'

    assert any(map(lambda m: blocks_prefix in m, caplog.messages))


def test_auto_exception_logging(caplog) -> None:  # type: ignore
    """Test if the stacktrace is extracted correctly when using log.exception"""
    log_msg = "Exception!"
    service_config = FormatConfig(service="testrunner", environment="test", extra_fields={"foo": "bar", "raven": "caw"})
    formatter = SlackFormatter.default(service_config)
    slack_handler.setFormatter(formatter)

    with pytest.raises(Exception):
        try:
            1 / 0
        except Exception:
            logger.exception(log_msg)
            raise

    blocks_prefix = '{"blocks": [{"text": {"text": ":x: ERROR | testrunner", "type": "plain_text"}, "type": "header"}, {"elements": [{"text": ":point_right: test, testrunner", "type": "mrkdwn"}], "type": "context"}, {"type": "divider"}, {"text": {"text": "Exception!", "type": "mrkdwn"}, "type": "section"}, {"text": {"text": "```Traceback (most recent call last):'

    assert any(map(lambda m: blocks_prefix in m, caplog.messages))
