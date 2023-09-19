import json
import logging

from slack_logger import DEFAULT_EMOJIS

DEFAULT_ADDITIONAL_FIELDS: dict[str, dict[str, str]] = {
    "foo": {"text": "*foo*\nbar", "type": "mrkdwn"},
    "raven": {"text": "*raven*\ncaw", "type": "mrkdwn"},
}


def default_msg(
    log_msg: str, levelno: int, additional_fields_dict: dict[str, dict[str, str]] = DEFAULT_ADDITIONAL_FIELDS
) -> str:
    additional_fields: list[dict[str, str]] = list(additional_fields_dict.values())
    emoji = DEFAULT_EMOJIS.get(levelno)
    level_name = logging.getLevelName(levelno)
    return json.dumps(
        {
            "blocks": [
                {"text": {"text": f"{emoji} {level_name} | testrunner", "type": "plain_text"}, "type": "header"},
                {"elements": [{"text": ":point_right: test, testrunner", "type": "mrkdwn"}], "type": "context"},
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
    level_name = logging.getLevelName(levelno)
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
