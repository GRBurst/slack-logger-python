import logging

import pytest

from slack_logger import FilterConfig, FilterType, FormatConfig, SlackFilter, SlackFormatter, SlackHandler

from .utils import default_msg, text_msg

logger = logging.getLogger("FilterTest")

# Setup test handler
slack_handler = SlackHandler.dummy()
slack_handler.setLevel(logging.WARNING)
logger.addHandler(slack_handler)


@pytest.fixture(autouse=True)
def cleanup(caplog) -> None:  # type: ignore # noqa: ANN001
    caplog.clear()
    slack_handler.setFormatter(None)
    slack_handler.filters = []
    yield slack_handler
    slack_handler.setFormatter(None)
    slack_handler.filters = []
    caplog.clear()


def test_allow_any_list_text_filter(caplog) -> None:  # type: ignore # noqa: ANN001
    """Test if allow list filters works if any provided field matches"""
    log_msg = "warning from basic_text_filter"

    # We allow logs from test environment
    slack_filter10 = SlackFilter(config=FilterConfig(environment="test", filter_type=FilterType.AnyAllowList))
    slack_handler.addFilter(slack_filter10)

    # Log from test environment
    logger.warning("%s in test and allow listed test", log_msg, extra={"filter": {"environment": "test"}})

    # Log from dev environment
    logger.warning("%s in dev and allow listed test", log_msg, extra={"filter": {"environment": "dev"}})

    assert text_msg(f"{log_msg} in test and allow listed test") in caplog.messages
    assert text_msg(f"{log_msg} in dev and allow listed test") not in caplog.messages


def test_allow_all_list_text_filter(caplog) -> None:  # type: ignore # noqa: ANN001
    """Test if allow list filters works if all provided field match"""
    log_msg = "warning from basic_text_filter"

    # We allow logs in test environment with extra_field {"cow": "moo"}
    slack_filter11 = SlackFilter(
        config=FilterConfig(environment="test", extra_fields={"cow": "moo"}, filter_type=FilterType.AllAllowList)
    )
    slack_handler.addFilter(slack_filter11)

    # Log from test environment
    logger.warning("%s in test, allow listed test, no cow", log_msg, extra={"filter": {"environment": "test"}})
    logger.warning(
        "%s in test, allow listed test, english cow",
        log_msg,
        extra={"filter": {"environment": "test", "extra_fields": {"cow": "moo"}}},
    )
    logger.warning(
        "%s in dev, allow listed test, english cow",
        log_msg,
        extra={"filter": {"environment": "dev", "extra_fields": {"cow": "moo"}}},
    )
    logger.warning(
        "%s in test, allow listed test, german cow",
        log_msg,
        extra={"filter": {"environment": "test", "extra_fields": {"cow": "muh"}}},
    )

    assert text_msg(f"{log_msg} in test, allow listed test, no cow") not in caplog.messages
    assert text_msg(f"{log_msg} in test, allow listed test, english cow") in caplog.messages
    assert text_msg(f"{log_msg} in dev, allow listed test, english cow") not in caplog.messages
    assert text_msg(f"{log_msg} in test, allow listed test, german cow") not in caplog.messages


def test_deny_any_list_text_filter(caplog) -> None:  # type: ignore # noqa: ANN001
    """Test if deny list filters works if any provided field match"""
    log_msg = "warning from basic_text_filter"

    # We deny list logs from "test" environment
    slack_filter20 = SlackFilter(config=FilterConfig(environment="test", filter_type=FilterType.AnyDenyList))
    slack_handler.addFilter(slack_filter20)

    # Log from test environment
    logger.warning("%s in test and deny listed test", log_msg, extra={"filter": {"environment": "test"}})

    # Log from dev environment
    logger.warning("%s in dev and deny listed test", log_msg, extra={"filter": {"environment": "dev"}})

    assert text_msg(f"{log_msg} in test and deny listed test") not in caplog.messages
    assert text_msg(f"{log_msg} in dev and deny listed test") in caplog.messages


def test_deny_all_list_text_filter(caplog) -> None:  # type: ignore # noqa: ANN001
    """Test if deny list filters works if any provided field match"""
    log_msg = "warning from basic_text_filter"

    # We deny list logs from "test" environment
    slack_filter30 = SlackFilter(
        config=FilterConfig(service="testrunner", extra_fields={"foo": "bar"}, filter_type=FilterType.AllDenyList)
    )
    slack_handler.addFilter(slack_filter30)

    # Log with matching config
    logger.warning(
        "%s with match all deny listed test",
        log_msg,
        extra={"filter": {"service": "testrunner", "extra_fields": {"foo": "bar"}}},
    )

    # Log with different foo
    logger.warning(
        "%s without match all deny listed test",
        log_msg,
        extra={"filter": {"service": "testrunner", "extra_fields": {"foo": "muh"}}},
    )

    assert text_msg(f"{log_msg} with match all deny listed test") not in caplog.messages
    assert text_msg(f"{log_msg} without match all deny listed test") in caplog.messages


def test_allow_any_list_blocks_filter(caplog) -> None:  # type: ignore # noqa: ANN001
    """Test if dey list filters works if any provided field match"""
    log_msg = "warning from basic_blocks_filter"

    # We define to be in test environment
    test_config = FormatConfig(service="testrunner", environment="test", extra_fields={"foo": "bar", "raven": "caw"})
    formatter = SlackFormatter.default(test_config)
    slack_handler.setFormatter(formatter)

    # We allow logs from test environment
    slack_filter10 = SlackFilter(config=FilterConfig(environment="test", filter_type=FilterType.AnyAllowList))
    slack_handler.addFilter(slack_filter10)

    # Log from test environment
    logger.warning("%s in test and allow listed test", log_msg)

    # We define to be in dev environment
    dev_config = FormatConfig(service="testrunner", environment="dev", extra_fields={"foo": "bar", "raven": "caw"})

    # We allow logs from dev environment
    formatter = SlackFormatter.default(dev_config)
    slack_handler.setFormatter(formatter)

    # Log from dev environment
    logger.warning("%s in dev and allow listed test", log_msg)

    assert default_msg(log_msg=f"{log_msg} in test and allow listed test", levelno=logging.WARNING) in caplog.messages
    assert (
        default_msg(log_msg=f"{log_msg} in dev and allow listed test", levelno=logging.WARNING) not in caplog.messages
    )


def test_allow_all_list_regex_text_filter(caplog) -> None:  # type: ignore # noqa: ANN001
    """Test if allow list filters works if all provided field match"""
    log_msg = "warning from basic_text_filter"

    # We allow logs in test environment with extra_field {"cow": "moo"}
    slack_filter11 = SlackFilter(
        config=FilterConfig(
            environment="test", extra_fields={"cow": "m.*"}, filter_type=FilterType.AllAllowList, use_regex=True
        )
    )
    slack_handler.addFilter(slack_filter11)

    # Log from test environment
    logger.warning("%s in test, allow listed test, no cow", log_msg, extra={"filter": {"environment": "test"}})
    logger.warning(
        "%s in test, allow listed test, english cow",
        log_msg,
        extra={"filter": {"environment": "test", "extra_fields": {"cow": "moo"}}},
    )
    logger.warning(
        "%s in dev, allow listed test, english cow",
        log_msg,
        extra={"filter": {"environment": "dev", "extra_fields": {"cow": "moo"}}},
    )
    logger.warning(
        "%s in test, allow listed test, german cow",
        log_msg,
        extra={"filter": {"environment": "test", "extra_fields": {"cow": "muh"}}},
    )

    assert text_msg(f"{log_msg} in test, allow listed test, no cow") not in caplog.messages
    assert text_msg(f"{log_msg} in test, allow listed test, english cow") in caplog.messages
    assert text_msg(f"{log_msg} in dev, allow listed test, english cow") not in caplog.messages
    assert text_msg(f"{log_msg} in test, allow listed test, german cow") in caplog.messages


def test_deny_any_list_regex_context_filter(caplog) -> None:  # type: ignore # noqa: ANN001
    """Test if combined filters works"""
    log_msg = "error from basic_text_filter on context"

    # We allow only logs from prod but deny logs with a context containing "job"
    slack_filter21 = SlackFilter(config=FilterConfig(environment="prod"))
    slack_filter22 = SlackFilter(
        config=FilterConfig(context=[".*job.*"], filter_type=FilterType.AnyDenyList, use_regex=True)
    )
    slack_handler.addFilter(slack_filter21)
    slack_handler.addFilter(slack_filter22)

    # Log from dev environment
    logger.error(
        "%s in dev and allow listed prod, deny listed job context", log_msg, extra={"filter": {"environment": "dev"}}
    )

    # Log from prod environment, but not with a "job" context
    logger.error(
        "%s in prod no job and allow listed prod, deny listed job context",
        log_msg,
        extra={"filter": {"environment": "prod", "context": ["foo", "bar"]}},
    )

    # Log from prod environment with "job" context
    logger.error(
        "%s in prod in job and allow listed prod, deny listed job context",
        log_msg,
        extra={"filter": {"environment": "prod", "context": ["foo", "job", "bar"]}},
    )

    assert text_msg(f"{log_msg} in dev and allow listed prod, deny listed job context") not in caplog.messages
    assert text_msg(f"{log_msg} in prod no job and allow listed prod, deny listed job context") in caplog.messages
    assert text_msg(f"{log_msg} in prod in job and allow listed prod, deny listed job context") not in caplog.messages
