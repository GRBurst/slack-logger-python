import asyncio
import json
import logging
from abc import ABC, abstractmethod
from enum import Enum
from logging import LogRecord
from typing import Any, Dict, Optional, Sequence, Union

from attrs import define
from slack_sdk.models.attachments import Attachment
from slack_sdk.models.blocks import Block, DividerBlock, HeaderBlock, SectionBlock
from slack_sdk.models.blocks.basic_components import MarkdownTextObject, PlainTextObject
from slack_sdk.webhook.async_client import AsyncWebhookClient
from slack_sdk.webhook.webhook_response import WebhookResponse

log = logging.getLogger("slack_logger")
log.setLevel(logging.DEBUG)

# Maps log levels to emojs
DEFAULT_EMOJIS = {
    logging.CRITICAL: ":fire:",
    logging.ERROR: ":x:",
    logging.FATAL: ":x:",
    logging.WARNING: ":warning:",
    logging.WARN: ":warning:",
    logging.INFO: ":bell:",
    logging.DEBUG: ":microscope:",
    logging.NOTSET: ":mega:",
}


@define
class Configuration:
    service: Optional[str] = None
    environment: Optional[str] = None
    emojis: Dict[int, str] = DEFAULT_EMOJIS
    extra_fields: Dict[str, str] = {}


@define
class MessageDesign(ABC):
    @abstractmethod
    def format_blocks(self, record: LogRecord) -> Sequence[Optional[Block]]:
        pass

    def format(self, record: LogRecord) -> str:
        maybe_blocks: Sequence[Optional[Block]] = self.format_blocks(record=record)
        blocks: Sequence[Block] = [b for b in maybe_blocks if b is not None]
        str_blocks: str = json.dumps(list(map(lambda block: block.to_dict(), blocks)))
        log.debug(f"str_blocks: {str_blocks}")
        return str_blocks


@define
class NoDesign(MessageDesign):
    def format_blocks(self, record: LogRecord) -> Sequence[Optional[Block]]:
        return [SectionBlock(text=PlainTextObject(text=record.getMessage()))]


@define
class MinimalDesign(MessageDesign):
    config: Configuration

    def format_blocks(self, record: LogRecord) -> Sequence[Optional[Block]]:
        level = record.levelname
        message = record.getMessage()
        icon = self.config.emojis.get(record.levelno)

        header: HeaderBlock
        if icon is not None:
            header = HeaderBlock(text=PlainTextObject(text=f"{icon} {level} | {self.config.service}"))
        else:
            header = HeaderBlock(text=PlainTextObject(text=f"{level} | {self.config.service}"))

        body = SectionBlock(text=MarkdownTextObject(text=message))
        default_blocks: Sequence[Block] = [
            header,
            body,
        ]

        return default_blocks


@define
class RichDesign(MessageDesign):
    config: Configuration

    def format_blocks(self, record: LogRecord) -> Sequence[Optional[Block]]:
        level = record.levelname
        message = record.getMessage()
        icon = self.config.emojis.get(record.levelno)

        dynamic_extra_fields = getattr(record, "extra_fields", {})
        all_extra_fields = {**self.config.extra_fields, **dynamic_extra_fields}

        header: HeaderBlock
        if icon is not None:
            header = HeaderBlock(text=PlainTextObject(text=f"{icon} {level} | {self.config.service}"))
        else:
            header = HeaderBlock(text=PlainTextObject(text=f"{level} | {self.config.service}"))

        body = SectionBlock(text=MarkdownTextObject(text=message))

        error: Optional[SectionBlock] = None
        if record.exc_info is not None:
            error = SectionBlock(text=MarkdownTextObject(text=f"```{record.exc_text}```"))

        fields = SectionBlock(
            fields=[
                MarkdownTextObject(text=f"*Environment*\n{self.config.environment}"),
                MarkdownTextObject(text=f"*Service*\n{self.config.service}"),
            ]
            + [MarkdownTextObject(text=f"*{key}*\n{value}") for key, value in all_extra_fields.items()]
        )

        maybe_blocks: Sequence[Optional[Block]] = [
            header,
            DividerBlock(),
            body,
            error,
            DividerBlock(),
            fields,
        ]

        return maybe_blocks


class SlackFormatter(logging.Formatter):
    design: MessageDesign
    config: Optional[Configuration]

    def __init__(self, design: MessageDesign, config: Optional[Configuration] = None):
        super(SlackFormatter, self).__init__()
        self.design = design
        self.config = config

    @classmethod
    def plain(cls, config: Optional[Configuration] = None) -> "SlackFormatter":
        return cls(design=NoDesign(), config=config)

    @classmethod
    def minimal(cls, config: Configuration) -> "SlackFormatter":
        return cls(design=MinimalDesign(config), config=config)

    @classmethod
    def default(cls, config: Configuration) -> "SlackFormatter":
        return cls(design=RichDesign(config), config=config)

    def format(self, record: LogRecord) -> str:
        return self.design.format(record)


# show = True:  log the values in the configuration
# show = False: hide the values in the configuration
# Injection filter
# https://docs.python.org/3/howto/logging-cookbook.html#using-filters-to-impart-contextual-information
class FilterType(Enum):
    AnyWhitelist = "AnyWhitelist"
    AllWhitelist = "AllWhitelist"
    AnyBlacklist = "AnyBlacklist"
    AllBlacklist = "AllBlacklist"


class SlackFilter(logging.Filter):
    config: Configuration
    tpe: FilterType

    def __init__(self, config: Configuration, filterType: FilterType = FilterType.AnyWhitelist):
        super(SlackFilter, self).__init__()
        self.config = config
        self.tpe = filterType

    @classmethod
    def filter_by_fields(
        cls, fields: Dict[str, str], filterType: FilterType = FilterType.AnyWhitelist
    ) -> "SlackFilter":
        return cls(Configuration(extra_fields=fields), filterType=filterType)

    @classmethod
    def hide_by_fields(cls, fields: Dict[str, str], filterType: FilterType = FilterType.AnyBlacklist) -> "SlackFilter":
        return cls(Configuration(extra_fields=fields), filterType=filterType)

    def filterConfig(self, serviceConfig: Configuration, record: LogRecord) -> bool:
        res_list = []
        if self.config.service is not None:
            res_list.append(serviceConfig.service == self.config.service)
        if self.config.environment is not None:
            res_list.append(serviceConfig.environment == self.config.environment)
        if self.config.extra_fields != {}:
            for f in self.config.extra_fields.items():
                res_list.append(f in serviceConfig.extra_fields.items())

        res: bool
        match self.tpe:
            case FilterType.AnyWhitelist:
                res = any(res_list)
            case FilterType.AllWhitelist:
                res = all(res_list)
            case FilterType.AnyBlacklist:
                res = not all(res_list)
            case FilterType.AllBlacklist:
                res = not any(res_list)

        log.debug(f"final result ({self.tpe}): res({res}) = {res_list}")
        return res

    def filter(self, record: LogRecord) -> bool:
        log_filters = getattr(record, "filter", None)
        if log_filters is None:
            return True

        extra_fields = log_filters.get("extra_fields", {})
        log.debug(f"EXTRA FIELDS: {extra_fields}")
        rconfig: Configuration = Configuration(
            service=log_filters.get("service", None),
            environment=log_filters.get("environment", None),
            extra_fields=log_filters.get("extra_fields", {}),
        )
        return self.filterConfig(serviceConfig=rconfig, record=record)


# class ConfigFilter(SlackFilter):


@define
class DummyClient(AsyncWebhookClient):
    url: str = ""

    async def send(
        self,
        *,
        text: Optional[str] = None,
        attachments: Optional[Sequence[Union[Dict[str, Any], Attachment]]] = None,
        blocks: Optional[Sequence[Union[Dict[str, Any], Block]]] = None,
        response_type: Optional[str] = None,
        replace_original: Optional[bool] = None,
        delete_original: Optional[bool] = None,
        unfurl_links: Optional[bool] = None,
        unfurl_media: Optional[bool] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> WebhookResponse:
        assert text is not None or blocks is not None

        t: str
        if text is None and blocks is not None:
            res = []
            for block in blocks:
                assert isinstance(block, Block)
                res.append(block.to_dict())
            t = json.dumps({"blocks": res})
        else:
            t = json.dumps({"text": str(text)})

        log.info(t)
        return WebhookResponse(url="", status_code=200, body=t, headers={})


class SlackHandler(logging.Handler):
    client: AsyncWebhookClient

    def __init__(self, client: AsyncWebhookClient):
        super(SlackHandler, self).__init__()
        self.client = client

    @classmethod
    def from_webhook(cls, webhook_url: str) -> "SlackHandler":
        return cls(
            client=AsyncWebhookClient(webhook_url),
        )

    @classmethod
    def dummy(cls) -> "SlackHandler":
        return cls(client=DummyClient())

    async def send_text_via_webhook(self, text: str) -> str:
        log.debug(text)
        response = await self.client.send(text=text)  # type: ignore
        assert response.status_code == 200
        # assert response.body == "ok"
        return str(response.body)

    async def send_blocks_via_webhook(self, blocks: str) -> str:
        # parsed_blocks = json.loads(blocks)
        block_seq = Block.parse_all(json.loads(blocks))
        response = await self.client.send(blocks=block_seq)
        assert response.status_code == 200
        # assert response.body == "ok"
        return str(response.body)

    def emit(self, record: LogRecord) -> None:
        try:
            if isinstance(self.formatter, SlackFormatter):
                formatted_message = self.format(record)
                log.debug(f"formatted_message: {formatted_message}")
                asyncio.run(self.send_blocks_via_webhook(blocks=formatted_message))
            else:
                formatted_message = self.format(record)
                log.debug(f"formatted_message: {formatted_message}")
                asyncio.run(self.send_text_via_webhook(text=formatted_message))

            # log.debug(f"format: {format}")
            # asyncio.run(self.send_message_via_webhook(message=formatted_message))
            # asyncio.run(self.send_blocks_via_webhook(blocks=formatted_message))
        except Exception:
            self.handleError(record)

    def handle(self, record: LogRecord) -> bool:
        # This pre-filters the messages with the Slack Filters
        if isinstance(self.formatter, SlackFormatter) and self.formatter.config is not None:
            format_config: Configuration = self.formatter.config
            for sf in self.filters:
                if isinstance(sf, SlackFilter):
                    res = sf.filterConfig(serviceConfig=format_config, record=record)
                    if not res:
                        return False

        return super().handle(record)
