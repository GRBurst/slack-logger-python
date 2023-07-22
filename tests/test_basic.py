import json
import logging
from typing import Dict, List

import pytest

from slack_logger import DEFAULT_EMOJIS, Configuration, FilterType, SlackFilter, SlackFormatter, SlackHandler

logger = logging.getLogger("LocalTest")

# Log to console as well
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter("%(asctime)s %(name)s|%(levelname)s: %(message)s"))
logger.addHandler(stream_handler)

# Setup test handler
slack_handler = SlackHandler.dummy()
slack_handler.setLevel(logging.WARN)
logger.addHandler(slack_handler)


# Check if only correct level is logged
def basic_logging(log_msg: str) -> None:
    logger.info(f"unformatted info {log_msg}")
    logger.warning(f"unformatted warning {log_msg}")
    logger.error(f"unformatted error {log_msg}")

    formatter = SlackFormatter.plain()
    slack_handler.setFormatter(formatter)
    logger.info(f"plain info {log_msg}")
    logger.warning(f"plain warning {log_msg}")
    logger.error(f"plain error {log_msg}")

    minimal_config = Configuration(service="testrunner", environment="test")
    formatter = SlackFormatter.minimal(minimal_config)
    slack_handler.setFormatter(formatter)
    logger.info(f"minimal info {log_msg}")
    logger.warning(f"minimal warning {log_msg}")
    logger.error(f"minimal error {log_msg}")

    service_config = Configuration(
        service="testrunner", environment="test", extra_fields={"foo": "bar", "raven": "caw"}
    )
    formatter = SlackFormatter.default(service_config)
    slack_handler.setFormatter(formatter)
    logger.info(f"default info {log_msg}")
    logger.warning(f"default warning {log_msg}")
    logger.error(f"default error {log_msg}")


def dynamic_fields(log_msg: str) -> None:
    service_config = Configuration(
        service="testrunner", environment="test", extra_fields={"foo": "bar", "raven": "caw"}
    )
    formatter = SlackFormatter.default(service_config)
    slack_handler.setFormatter(formatter)
    logger.warning(f"additional {log_msg}", extra={"extra_fields": {"cow": "moo"}})
    logger.error(f"overwrite {log_msg}", extra={"extra_fields": {"foo": "baba"}})


def exception_logging(log_msg: str) -> None:
    service_config = Configuration(
        service="testrunner", environment="test", extra_fields={"foo": "bar", "raven": "caw"}
    )
    formatter = SlackFormatter.default(service_config)
    slack_handler.setFormatter(formatter)

    try:
        1 / 0
    except Exception as e:
        logger.error(log_msg, exc_info=e)
        raise e


def auto_exception_logging(log_msg: str) -> None:
    service_config = Configuration(
        service="testrunner", environment="test", extra_fields={"foo": "bar", "raven": "caw"}
    )
    formatter = SlackFormatter.default(service_config)
    slack_handler.setFormatter(formatter)

    try:
        1 / 0
    except Exception as e:
        logger.exception(log_msg)
        raise e


def basic_text_filter(log_msg: str) -> None:  # type: ignore
    # Whitelist
    ## We allow logs from test environment
    slackFilter10 = SlackFilter(config=Configuration(environment="test"), filterType=FilterType.AnyWhitelist)
    slack_handler.addFilter(slackFilter10)

    ### Log from test environment
    logger.warning(f"{log_msg} in test and whitelisted test", extra={"filter": {"environment": "test"}})

    ### Log from dev environment
    logger.warning(f"{log_msg} in dev and whitelisted test", extra={"filter": {"environment": "dev"}})

    # Cleanup
    slack_handler.removeFilter(slackFilter10)
    assert len(slack_handler.filters) == 0

    ## We allow logs in test environment with extra_field {"cow": "moo"}
    slackFilter11 = SlackFilter(
        config=Configuration(environment="test", extra_fields={"cow": "moo"}), filterType=FilterType.AllWhitelist
    )
    slack_handler.addFilter(slackFilter11)

    ### Log from test environment
    logger.warning(f"{log_msg} in test, whitelisted test, no cow", extra={"filter": {"environment": "test"}})
    logger.warning(
        f"{log_msg} in test, whitelisted test, english cow",
        extra={"filter": {"environment": "test", "extra_fields": {"cow": "moo"}}},
    )
    logger.warning(
        f"{log_msg} in dev, whitelisted test, english cow",
        extra={"filter": {"environment": "dev", "extra_fields": {"cow": "moo"}}},
    )
    logger.warning(
        f"{log_msg} in test, whitelisted test, german cow",
        extra={"filter": {"environment": "test", "extra_fields": {"cow": "muh"}}},
    )

    # Cleanup
    slack_handler.removeFilter(slackFilter11)
    assert len(slack_handler.filters) == 0

    # Blacklist
    ## We blacklist logs from "test" environment
    slackFilter20 = SlackFilter(config=Configuration(environment="test"), filterType=FilterType.AnyBlacklist)
    slack_handler.addFilter(slackFilter20)

    ## Log from test environment
    logger.warning(f"{log_msg} in test and blacklisted test", extra={"filter": {"environment": "test"}})

    ## Log from dev environment
    logger.warning(f"{log_msg} in dev and blacklisted test", extra={"filter": {"environment": "dev"}})

    # Cleanup
    slack_handler.removeFilter(slackFilter20)
    assert len(slack_handler.filters) == 0


def basic_blocks_filter(log_msg: str) -> None:  # type: ignore
    service_config = Configuration(
        service="testrunner", environment="test", extra_fields={"foo": "bar", "raven": "caw"}
    )
    formatter = SlackFormatter.default(service_config)
    slack_handler.setFormatter(formatter)
    # Whitelist
    ## We allow logs from test environment
    slackFilter10 = SlackFilter(config=Configuration(environment="test"), filterType=FilterType.AnyWhitelist)
    slack_handler.addFilter(slackFilter10)

    ### Log from test environment
    logger.warning(f"{log_msg} in test and whitelisted test")

    ### Log from dev environment
    service_config = Configuration(service="testrunner", environment="dev", extra_fields={"foo": "bar", "raven": "caw"})
    formatter = SlackFormatter.default(service_config)
    slack_handler.setFormatter(formatter)
    logger.warning(f"{log_msg} in dev and whitelisted test")

    # Cleanup
    slack_handler.removeFilter(slackFilter10)
    assert len(slack_handler.filters) == 0


DEFAULT_ADDITIONAL_FIELDS: Dict[str, Dict[str, str]] = {
    "env": {"text": "*Environment*\ntest", "type": "mrkdwn"},
    "service": {"text": "*Service*\ntestrunner", "type": "mrkdwn"},
    "foo": {"text": "*foo*\nbar", "type": "mrkdwn"},
    "raven": {"text": "*raven*\ncaw", "type": "mrkdwn"},
}


def default_msg(
    log_msg: str, levelno: int, additional_fields_dict: Dict[str, Dict[str, str]] = DEFAULT_ADDITIONAL_FIELDS
) -> str:
    additional_fields: List[Dict[str, str]] = list(additional_fields_dict.values())
    emoji = DEFAULT_EMOJIS.get(levelno)
    level_name = logging._levelToName.get(levelno)
    return json.dumps(
        {
            "blocks": [
                {"text": {"text": f"{emoji} {level_name} | testrunner", "type": "plain_text"}, "type": "header"},
                {"type": "divider"},
                {
                    "text": {"text": log_msg, "type": "mrkdwn"},
                    "type": "section",
                },
                {"type": "divider"},
                {
                    "fields": additional_fields,
                    "type": "section",
                },
            ]
        }
    )


def minimal_msg(log_msg: str, levelno: int) -> str:
    emoji = DEFAULT_EMOJIS.get(levelno)
    level_name = logging._levelToName.get(levelno)
    return json.dumps(
        {
            "blocks": [
                {"text": {"text": f"{emoji} {level_name} | testrunner", "type": "plain_text"}, "type": "header"},
                {
                    "text": {"text": log_msg, "type": "mrkdwn"},
                    "type": "section",
                },
            ]
        }
    )


def plain_msg(log_msg: str) -> str:
    return json.dumps(
        {
            "blocks": [
                {
                    "text": {"text": log_msg, "type": "plain_text"},
                    "type": "section",
                }
            ]
        }
    )


def text_msg(log_msg: str) -> str:
    return json.dumps({"text": log_msg})


# ignore types of tests because of caplog fixtures
class TestBasicLogging:
    def test_basic_logging(self, caplog) -> None:  # type: ignore
        slack_handler.setFormatter(None)
        caplog.clear()
        log_msg = "from basic_text_filter"

        basic_logging(log_msg)

        assert text_msg(f"unformatted info {log_msg}") not in caplog.messages
        assert text_msg(f"unformatted warning {log_msg}") in caplog.messages
        assert text_msg(f"unformatted error {log_msg}") in caplog.messages

        # Like unformatted (no formatter), but with a dummy formatter and in blocks
        assert plain_msg(f"plain info {log_msg}") not in caplog.messages
        assert plain_msg(f"plain warning {log_msg}") in caplog.messages
        assert plain_msg(f"plain error {log_msg}") in caplog.messages

        assert minimal_msg(f"minimal info {log_msg}", levelno=logging.INFO) not in caplog.messages
        assert minimal_msg(f"minimal warning {log_msg}", levelno=logging.WARNING) in caplog.messages
        assert minimal_msg(f"minimal error {log_msg}", levelno=logging.ERROR) in caplog.messages

        assert default_msg(f"default info {log_msg}", levelno=logging.INFO) not in caplog.messages
        assert default_msg(f"default warning {log_msg}", levelno=logging.WARNING) in caplog.messages
        assert default_msg(f"default error {log_msg}", levelno=logging.ERROR) in caplog.messages

    def test_dynamic_fields(self, caplog) -> None:  # type: ignore
        slack_handler.setFormatter(None)
        caplog.clear()
        log_msg = "from test_dynamic_fields"

        dynamic_fields(log_msg)

        fields_a: Dict[str, Dict[str, str]] = DEFAULT_ADDITIONAL_FIELDS.copy()
        fields_a.update({"cow": {"text": "*cow*\nmoo", "type": "mrkdwn"}})
        assert (
            default_msg(f"additional {log_msg}", levelno=logging.WARNING, additional_fields_dict=fields_a)
            in caplog.messages
        )

        fields_o: Dict[str, Dict[str, str]] = DEFAULT_ADDITIONAL_FIELDS.copy()
        fields_o.update({"foo": {"text": "*foo*\nbaba", "type": "mrkdwn"}})
        assert (
            default_msg(f"overwrite {log_msg}", levelno=logging.ERROR, additional_fields_dict=fields_o)
            in caplog.messages
        )

    def test_exception_logging(self, caplog) -> None:  # type: ignore
        slack_handler.setFormatter(None)
        caplog.clear()

        log_msg = "Error!"
        with pytest.raises(ZeroDivisionError):
            exception_logging(log_msg)

        blocks_prefix = '{"blocks": [{"text": {"text": ":x: ERROR | testrunner", "type": "plain_text"}, "type": "header"}, {"type": "divider"}, {"text": {"text": "Error!", "type": "mrkdwn"}, "type": "section"}, {"text": {"text": "```Traceback (most recent call last):'

        assert any(map(lambda m: blocks_prefix in m, caplog.messages))

    def test_auto_exception_logging(self, caplog) -> None:  # type: ignore
        slack_handler.setFormatter(None)
        caplog.clear()

        log_msg = "Exception!"
        with pytest.raises(Exception):
            auto_exception_logging(log_msg)

        blocks_prefix = '{"blocks": [{"text": {"text": ":x: ERROR | testrunner", "type": "plain_text"}, "type": "header"}, {"type": "divider"}, {"text": {"text": "Exception!", "type": "mrkdwn"}, "type": "section"}, {"text": {"text": "```Traceback (most recent call last):'

        assert any(map(lambda m: blocks_prefix in m, caplog.messages))

    def test_filters(self, caplog) -> None:  # type: ignore
        slack_handler.setFormatter(None)
        caplog.clear()

        log_msg = "warning from basic_text_filter"
        basic_text_filter(log_msg)
        assert text_msg(f"{log_msg} in test and whitelisted test") in caplog.messages
        assert text_msg(f"{log_msg} in dev and whitelisted test") not in caplog.messages
        assert text_msg(f"{log_msg} in test and blacklisted test") not in caplog.messages
        assert text_msg(f"{log_msg} in dev and blacklisted test") in caplog.messages

        assert text_msg(f"{log_msg} in test, whitelisted test, no cow") not in caplog.messages
        assert text_msg(f"{log_msg} in test, whitelisted test, english cow") in caplog.messages
        assert text_msg(f"{log_msg} in dev, whitelisted test, english cow") not in caplog.messages
        assert text_msg(f"{log_msg} in test, whitelisted test, german cow") not in caplog.messages

        slack_handler.setFormatter(None)
        caplog.clear()

        log_msg = "warning from basic_blocks_filter"
        basic_blocks_filter(log_msg)
        assert (
            default_msg(log_msg=f"{log_msg} in test and whitelisted test", levelno=logging.WARNING) in caplog.messages
        )
        assert (
            default_msg(log_msg=f"{log_msg} in dev and whitelisted test", levelno=logging.WARNING)
            not in caplog.messages
        )
