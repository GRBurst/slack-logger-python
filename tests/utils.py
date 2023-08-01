import json
import logging
from typing import Dict, List

from slack_logger import DEFAULT_EMOJIS

DEFAULT_ADDITIONAL_FIELDS: Dict[str, Dict[str, str]] = {
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
    return json.dumps({"text": log_msg})
