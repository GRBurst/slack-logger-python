import asyncio
import json
import logging
from abc import ABC, abstractmethod
from logging import LogRecord
from typing import Dict, Optional, Sequence

from attrs import define
from slack_sdk.models.blocks import Block, DividerBlock, HeaderBlock, SectionBlock
from slack_sdk.models.blocks.basic_components import MarkdownTextObject, PlainTextObject
from slack_sdk.webhook.async_client import AsyncWebhookClient

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
    colors: Optional[Dict[str, str]] = None  # TODO: level -> color
    emojis: Dict[int, str] = DEFAULT_EMOJIS
    fields: Dict[str, str] = {}


@define
class MessageDesign(ABC):
    @abstractmethod
    def format_blocks(self, record: LogRecord) -> Sequence[Optional[Block]]:
        pass

    def format(self, record: LogRecord) -> str:
        maybe_blocks: Sequence[Optional[Block]] = self.format_blocks(record=record)
        print(f"Maybe blocks: {maybe_blocks}")
        blocks: Sequence[Block] = [b for b in maybe_blocks if b is not None]
        print(f"blocks: {blocks}")
        str_blocks: str = json.dumps(list(map(lambda block: block.to_dict(), blocks)))
        print(f"str_blocks: {str_blocks}")
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

        header = HeaderBlock(text=PlainTextObject(text=f"{icon} {level} | {self.config.service}"))
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

        header = HeaderBlock(text=PlainTextObject(text=f"{icon} {level} | {self.config.service}"))
        body = SectionBlock(text=MarkdownTextObject(text=message))

        error: Optional[SectionBlock] = None
        if record.exc_info is not None:
            error = SectionBlock(text=MarkdownTextObject(text=f"```{record.exc_text}```"))

        fields = SectionBlock(
            fields=[
                MarkdownTextObject(text=f"*Environment*\n{self.config.environment}"),
                MarkdownTextObject(text=f"*Service*\n{self.config.service}"),
            ]
            + [MarkdownTextObject(text=f"*{key}*\n{value}") for key, value in self.config.fields.items()]
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

    def __init__(self, design: MessageDesign):
        super(SlackFormatter, self).__init__()
        self.design = design

    @classmethod
    def plain(cls) -> "SlackFormatter":
        return cls(design=NoDesign())

    @classmethod
    def minimal(cls, config: Configuration) -> "SlackFormatter":
        return cls(design=MinimalDesign(config))

    @classmethod
    def default(cls, config: Configuration) -> "SlackFormatter":
        return cls(design=RichDesign(config))

    def format(self, record: LogRecord) -> str:
        print(f"slack formatter: {record}")
        return self.design.format(record)


class SlackHandler(logging.Handler):
    def __init__(self, client: AsyncWebhookClient):
        super(SlackHandler, self).__init__()
        self.client = client

    @classmethod
    def from_webhook(cls, webhook_url: str) -> "SlackHandler":
        return cls(
            client=AsyncWebhookClient(webhook_url),
        )

    async def send_message_via_webhook(self, message: str) -> str:
        response = await self.client.send(blocks=message)  # type: ignore
        assert response.status_code == 200
        assert response.body == "ok"
        return str(response.body)

    def emit(self, record: LogRecord) -> None:
        print("emit")
        try:
            print("emit")
            formatted_message = self.format(record)
            print(f"format: {format}")
            asyncio.run(self.send_message_via_webhook(message=formatted_message))
        except Exception:
            self.handleError(record)
