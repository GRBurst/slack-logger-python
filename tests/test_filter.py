import logging

import pytest

from slack_logger import Configuration as SlackConfiguration
from slack_logger import FilterType, SlackFilter, SlackFormatter, SlackHandler

from .utils import default_msg, text_msg

logger = logging.getLogger("FilterTest")

# Setup test handler
slack_handler = SlackHandler.dummy()
slack_handler.setLevel(logging.WARN)
logger.addHandler(slack_handler)


@pytest.fixture(autouse=True)
def cleanup(caplog) -> None:  # type: ignore
    caplog.clear()
    slack_handler.setFormatter(None)
    slack_handler.filters = []
    yield slack_handler
    slack_handler.setFormatter(None)
    slack_handler.filters = []
    caplog.clear()


def test_allow_any_list_text_filter(caplog) -> None:  # type: ignore
    """Test if allow list filters works if any provided field matches"""
    log_msg = "warning from basic_text_filter"

    # We allow logs from test environment
    slackFilter10 = SlackFilter(config=SlackConfiguration(environment="test"), filterType=FilterType.AnyAllowList)
    slack_handler.addFilter(slackFilter10)

    # Log from test environment
    logger.warning(f"{log_msg} in test and allow listed test", extra={"filter": {"environment": "test"}})

    # Log from dev environment
    logger.warning(f"{log_msg} in dev and allow listed test", extra={"filter": {"environment": "dev"}})

    assert text_msg(f"{log_msg} in test and allow listed test") in caplog.messages
    assert text_msg(f"{log_msg} in dev and allow listed test") not in caplog.messages


def test_allow_all_list_text_filter(caplog) -> None:  # type: ignore
    """Test if allow list filters works if all provided field match"""
    log_msg = "warning from basic_text_filter"

    # We allow logs in test environment with extra_field {"cow": "moo"}
    slackFilter11 = SlackFilter(
        config=SlackConfiguration(environment="test", extra_fields={"cow": "moo"}), filterType=FilterType.AllAllowList
    )
    slack_handler.addFilter(slackFilter11)

    # Log from test environment
    logger.warning(f"{log_msg} in test, allow listed test, no cow", extra={"filter": {"environment": "test"}})
    logger.warning(
        f"{log_msg} in test, allow listed test, english cow",
        extra={"filter": {"environment": "test", "extra_fields": {"cow": "moo"}}},
    )
    logger.warning(
        f"{log_msg} in dev, allow listed test, english cow",
        extra={"filter": {"environment": "dev", "extra_fields": {"cow": "moo"}}},
    )
    logger.warning(
        f"{log_msg} in test, allow listed test, german cow",
        extra={"filter": {"environment": "test", "extra_fields": {"cow": "muh"}}},
    )

    assert text_msg(f"{log_msg} in test, allow listed test, no cow") not in caplog.messages
    assert text_msg(f"{log_msg} in test, allow listed test, english cow") in caplog.messages
    assert text_msg(f"{log_msg} in dev, allow listed test, english cow") not in caplog.messages
    assert text_msg(f"{log_msg} in test, allow listed test, german cow") not in caplog.messages


def test_deny_any_list_text_filter(caplog) -> None:  # type: ignore
    """Test if deny list filters works if any provided field match"""
    log_msg = "warning from basic_text_filter"

    # We deny list logs from "test" environment
    slackFilter20 = SlackFilter(config=SlackConfiguration(environment="test"), filterType=FilterType.AnyDenyList)
    slack_handler.addFilter(slackFilter20)

    # Log from test environment
    logger.warning(f"{log_msg} in test and deny listed test", extra={"filter": {"environment": "test"}})

    # Log from dev environment
    logger.warning(f"{log_msg} in dev and deny listed test", extra={"filter": {"environment": "dev"}})

    assert text_msg(f"{log_msg} in test and deny listed test") not in caplog.messages
    assert text_msg(f"{log_msg} in dev and deny listed test") in caplog.messages


def test_deny_all_list_text_filter(caplog) -> None:  # type: ignore
    """Test if deny list filters works if any provided field match"""
    log_msg = "warning from basic_text_filter"

    # We deny list logs from "test" environment
    slackFilter30 = SlackFilter(
        config=SlackConfiguration(service="testrunner", extra_fields={"foo": "bar"}), filterType=FilterType.AllDenyList
    )
    slack_handler.addFilter(slackFilter30)

    # Log with matching config
    logger.warning(
        f"{log_msg} with match all deny listed test",
        extra={"filter": {"service": "testrunner", "extra_fields": {"foo": "bar"}}},
    )

    # Log with different foo
    logger.warning(
        f"{log_msg} without match all deny listed test",
        extra={"filter": {"service": "testrunner", "extra_fields": {"foo": "muh"}}},
    )

    assert text_msg(f"{log_msg} with match all deny listed test") not in caplog.messages
    assert text_msg(f"{log_msg} without match all deny listed test") in caplog.messages


def test_allow_any_list_blocks_filter(caplog) -> None:  # type: ignore
    """Test if dey list filters works if any provided field match"""
    log_msg = "warning from basic_blocks_filter"

    service_config = SlackConfiguration(
        service="testrunner", environment="test", extra_fields={"foo": "bar", "raven": "caw"}
    )

    formatter = SlackFormatter.default(service_config)
    slack_handler.setFormatter(formatter)

    # We allow logs from test environment
    slackFilter10 = SlackFilter(config=SlackConfiguration(environment="test"), filterType=FilterType.AnyAllowList)
    slack_handler.addFilter(slackFilter10)

    # Log from test environment
    logger.warning(f"{log_msg} in test and allow listed test")

    # We allow logs from dev environment
    service_config = SlackConfiguration(
        service="testrunner", environment="dev", extra_fields={"foo": "bar", "raven": "caw"}
    )
    formatter = SlackFormatter.default(service_config)
    slack_handler.setFormatter(formatter)

    # Log from dev environment
    logger.warning(f"{log_msg} in dev and allow listed test")

    assert default_msg(log_msg=f"{log_msg} in test and allow listed test", levelno=logging.WARNING) in caplog.messages
    assert (
        default_msg(log_msg=f"{log_msg} in dev and allow listed test", levelno=logging.WARNING) not in caplog.messages
    )


def test_allow_all_list_regex_text_filter(caplog) -> None:  # type: ignore
    """Test if allow list filters works if all provided field match"""
    log_msg = "warning from basic_text_filter"

    # We allow logs in test environment with extra_field {"cow": "moo"}
    slackFilter11 = SlackFilter(
        config=SlackConfiguration(environment="test", extra_fields={"cow": "moo"}), filterType=FilterType.AllAllowList
    )
    slack_handler.addFilter(slackFilter11)

    # Log from test environment
    logger.warning(f"{log_msg} in test, allow listed test, no cow", extra={"filter": {"environment": "test"}})
    logger.warning(
        f"{log_msg} in test, allow listed test, english cow",
        extra={"filter": {"environment": "test", "extra_fields": {"cow": "moo"}}},
    )
    logger.warning(
        f"{log_msg} in dev, allow listed test, english cow",
        extra={"filter": {"environment": "dev", "extra_fields": {"cow": "moo"}}},
    )
    logger.warning(
        f"{log_msg} in test, allow listed test, german cow",
        extra={"filter": {"environment": "test", "extra_fields": {"cow": "muh"}}},
    )

    assert text_msg(f"{log_msg} in test, allow listed test, no cow") not in caplog.messages
    assert text_msg(f"{log_msg} in test, allow listed test, english cow") in caplog.messages
    assert text_msg(f"{log_msg} in dev, allow listed test, english cow") not in caplog.messages
    assert text_msg(f"{log_msg} in test, allow listed test, german cow") not in caplog.messages
