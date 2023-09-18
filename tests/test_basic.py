import logging
from collections.abc import Generator

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
def cleanup(caplog) -> Generator:  # type: ignore # noqa: ANN001
    caplog.clear()
    slack_handler.setFormatter(None)
    slack_handler.filters = []
    yield slack_handler
    slack_handler.setFormatter(None)
    slack_handler.filters = []
    caplog.clear()


def test_basic_unformatted_logging(caplog) -> None:  # type: ignore # noqa: ANN001
    """Check if only correct level is logged when not using a SlackFormatter"""
    log_msg = "from basic_text_logging"

    logger.info("unformatted info %s", log_msg)
    logger.warning("unformatted warning %s", log_msg)
    logger.error("unformatted error %s", log_msg)

    assert text_msg(f"unformatted info {log_msg}") not in caplog.messages
    assert text_msg(f"unformatted warning {log_msg}") in caplog.messages
    assert text_msg(f"unformatted error {log_msg}") in caplog.messages


def test_basic_plain_formatted_logging(caplog) -> None:  # type: ignore # noqa: ANN001
    """Check if only correct level is logged when not using plain SlackFormatter"""
    log_msg = "from basic_text_logging"
    formatter = SlackFormatter.plain()
    slack_handler.setFormatter(formatter)

    logger.info("plain info %s", log_msg)
    logger.warning("plain warning %s", log_msg)
    logger.error("plain error %s", log_msg)

    assert plain_msg(f"plain info {log_msg}") not in caplog.messages
    assert plain_msg(f"plain warning {log_msg}") in caplog.messages
    assert plain_msg(f"plain error {log_msg}") in caplog.messages


def test_basic_minimal_formatted_logging(caplog) -> None:  # type: ignore # noqa: ANN001
    """Check if only correct level is logged when not using minimal SlackFormatter"""
    log_msg = "from basic_text_logging"
    minimal_config = FormatConfig(service="testrunner", environment="test")
    formatter = SlackFormatter.minimal(minimal_config)
    slack_handler.setFormatter(formatter)

    logger.info("minimal info %s", log_msg)
    logger.warning("minimal warning %s", log_msg)
    logger.error("minimal error %s", log_msg)

    assert minimal_msg(f"minimal info {log_msg}", levelno=logging.INFO) not in caplog.messages
    assert minimal_msg(f"minimal warning {log_msg}", levelno=logging.WARNING) in caplog.messages
    assert minimal_msg(f"minimal error {log_msg}", levelno=logging.ERROR) in caplog.messages


def test_basic_default_formatted_logging(caplog) -> None:  # type: ignore # noqa: ANN001
    """Check if only correct level is logged when not using default SlackFormatter"""
    log_msg = "from basic_text_logging"
    service_config = FormatConfig(service="testrunner", environment="test", extra_fields={"foo": "bar", "raven": "caw"})
    formatter = SlackFormatter.default(service_config)
    slack_handler.setFormatter(formatter)

    logger.info("default info %s", log_msg)
    logger.warning("default warning %s", log_msg)
    logger.error("default error %s", log_msg)

    assert default_msg(f"default info {log_msg}", levelno=logging.INFO) not in caplog.messages
    assert default_msg(f"default warning {log_msg}", levelno=logging.WARNING) in caplog.messages
    assert default_msg(f"default error {log_msg}", levelno=logging.ERROR) in caplog.messages


# Logging with extra fields
def test_dynamic_fields_additional(caplog) -> None:  # type: ignore # noqa: ANN001
    """Test if adding extra fields to when creating log messages works"""
    log_msg = "from test_dynamic_fields"
    service_config = FormatConfig(service="testrunner", environment="test", extra_fields={"foo": "bar", "raven": "caw"})
    formatter = SlackFormatter.default(service_config)
    slack_handler.setFormatter(formatter)
    logger.warning("additional %s", log_msg, extra={"extra_fields": {"cow": "moo"}})

    fields_a: dict[str, dict[str, str]] = DEFAULT_ADDITIONAL_FIELDS.copy()
    fields_a.update({"cow": {"text": "*cow*\nmoo", "type": "mrkdwn"}})
    assert (
        default_msg(f"additional {log_msg}", levelno=logging.WARNING, additional_fields_dict=fields_a)
        in caplog.messages
    )


def test_dynamic_fields_overwrite(caplog) -> None:  # type: ignore # noqa: ANN001
    """Test if overwriting extra fields to when creating log messages works"""
    log_msg = "from test_dynamic_fields"
    service_config = FormatConfig(service="testrunner", environment="test", extra_fields={"foo": "bar", "raven": "caw"})
    formatter = SlackFormatter.default(service_config)
    slack_handler.setFormatter(formatter)

    logger.error("overwrite %s", log_msg, extra={"extra_fields": {"foo": "baba"}})

    fields_o: dict[str, dict[str, str]] = DEFAULT_ADDITIONAL_FIELDS.copy()
    fields_o.update({"foo": {"text": "*foo*\nbaba", "type": "mrkdwn"}})
    assert (
        default_msg(f"overwrite {log_msg}", levelno=logging.ERROR, additional_fields_dict=fields_o) in caplog.messages
    )


def test_exception_logging(caplog) -> None:  # type: ignore # noqa: ANN001
    """Test if the stacktrace is extracted correctly when providing exc_info to log.error"""
    log_msg = "Error!"
    service_config = FormatConfig(service="testrunner", environment="test", extra_fields={"foo": "bar", "raven": "caw"})
    formatter = SlackFormatter.default(service_config)
    slack_handler.setFormatter(formatter)

    def division() -> None:
        try:
            _res = 1 / 0
        except Exception as e:
            logger.error(log_msg, exc_info=e)  # noqa: TRY400 (allow logger.error instead logger.exception)
            raise

    with pytest.raises(ZeroDivisionError):
        division()

    blocks_prefix = '{"blocks": [{"text": {"text": ":x: ERROR | testrunner", "type": "plain_text"}, "type": "header"}, {"elements": [{"text": ":point_right: test, testrunner", "type": "mrkdwn"}], "type": "context"}, {"type": "divider"}, {"text": {"text": "Error!", "type": "mrkdwn"}, "type": "section"}, {"text": {"text": "```Traceback (most recent call last):'

    assert any(blocks_prefix in m for m in caplog.messages)


def test_auto_exception_logging(caplog) -> None:  # type: ignore # noqa: ANN001
    """Test if the stacktrace is extracted correctly when using log.exception"""
    log_msg = "Exception!"
    service_config = FormatConfig(service="testrunner", environment="test", extra_fields={"foo": "bar", "raven": "caw"})
    formatter = SlackFormatter.default(service_config)
    slack_handler.setFormatter(formatter)

    def division() -> None:
        try:
            _res = 1 / 0
        except Exception:
            logger.exception(log_msg)
            raise

    with pytest.raises(ZeroDivisionError):
        division()

    blocks_prefix = '{"blocks": [{"text": {"text": ":x: ERROR | testrunner", "type": "plain_text"}, "type": "header"}, {"elements": [{"text": ":point_right: test, testrunner", "type": "mrkdwn"}], "type": "context"}, {"type": "divider"}, {"text": {"text": "Exception!", "type": "mrkdwn"}, "type": "section"}, {"text": {"text": "```Traceback (most recent call last):'

    assert any(blocks_prefix in m for m in caplog.messages)
