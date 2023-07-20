import json
import logging
import os

import pytest

from slack_logger import Configuration, FilterType, SlackFilter, SlackFormatter, SlackHandler

logger = logging.getLogger("LocalTest")

# Log to console as well
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter("%(asctime)s %(name)s|%(levelname)s: %(message)s"))
logger.addHandler(stream_handler)

# Setup test handler
slack_handler = SlackHandler.dummy()
slack_handler.setLevel(logging.WARN)
logger.addHandler(slack_handler)


def basic_text_filter(caplog, log_msg: str) -> None:  # type: ignore
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


def basic_blocks_filter(caplog, log_msg: str) -> None:  # type: ignore
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


def default_msg(log_msg: str) -> str:
    return json.dumps(
        {
            "blocks": [
                {"text": {"text": ":warning: WARNING | testrunner", "type": "plain_text"}, "type": "header"},
                {"type": "divider"},
                {
                    "text": {"text": log_msg, "type": "mrkdwn"},
                    "type": "section",
                },
                {"type": "divider"},
                {
                    "fields": [
                        {"text": "*Environment*\ntest", "type": "mrkdwn"},
                        {"text": "*Service*\ntestrunner", "type": "mrkdwn"},
                        {"text": "*foo*\nbar", "type": "mrkdwn"},
                        {"text": "*raven*\ncaw", "type": "mrkdwn"},
                    ],
                    "type": "section",
                },
            ]
        }
    )


def plain_msg(log_msg: str) -> str:
    return json.dumps({"text": log_msg})


class TestBasicLogging:
    # ignore types of tests because of fixtures
    def test_filters(self, caplog) -> None:  # type: ignore
        caplog.at_level(logging.WARN)

        log_msg = "warning from basic_text_filter"
        basic_text_filter(caplog, log_msg)
        assert plain_msg(f"{log_msg} in test and whitelisted test") in caplog.messages
        assert plain_msg(f"{log_msg} in dev and whitelisted test") not in caplog.messages
        assert plain_msg(f"{log_msg} in test and blacklisted test") not in caplog.messages
        assert plain_msg(f"{log_msg} in dev and blacklisted test") in caplog.messages

        assert plain_msg(f"{log_msg} in test, whitelisted test, no cow") not in caplog.messages
        assert plain_msg(f"{log_msg} in test, whitelisted test, english cow") in caplog.messages
        assert plain_msg(f"{log_msg} in dev, whitelisted test, english cow") not in caplog.messages
        assert plain_msg(f"{log_msg} in test, whitelisted test, german cow") not in caplog.messages

        caplog.clear()

        log_msg = "warning from basic_blocks_filter"
        basic_blocks_filter(caplog, log_msg)
        assert default_msg(log_msg=f"{log_msg} in test and whitelisted test") in caplog.messages
        assert default_msg(log_msg=f"{log_msg} in dev and whitelisted test") not in caplog.messages

        caplog.clear()
