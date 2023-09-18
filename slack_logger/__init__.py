import asyncio
import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from enum import Enum
from logging import LogRecord
from typing import Any

from aiohttp.web_exceptions import HTTPOk
from attrs import Factory, asdict, define
from cattrs import structure
from slack_sdk.models.attachments import Attachment
from slack_sdk.models.blocks import Block, ContextBlock, DividerBlock, HeaderBlock, SectionBlock
from slack_sdk.models.blocks.basic_components import MarkdownTextObject, PlainTextObject
from slack_sdk.webhook.async_client import AsyncWebhookClient
from slack_sdk.webhook.webhook_response import WebhookResponse

log = logging.getLogger("slack_logger")
log.setLevel(logging.DEBUG)


class SendError(Exception):
    def __init__(self, code: int, msg: str) -> None:
        super().__init__(f"Slack responds unsuccessful with code {code}: {msg}")


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


class FilterType(Enum):
    AnyAllowList = "AnyAllowList"
    AllAllowList = "AllAllowList"
    AnyDenyList = "AnyDenyList"
    AllDenyList = "AllDenyList"


@define
class LogConfig:
    service: str | None = None
    environment: str | None = None
    context: list[str] = Factory(list)
    extra_fields: dict[str, str] = Factory(dict)


@define
class FormatConfig(LogConfig):
    emojis: dict[int, str] = DEFAULT_EMOJIS


@define
class FilterConfig(LogConfig):
    use_regex: bool = False
    filter_type: FilterType = FilterType.AnyAllowList


@define
class MessageDesign(ABC):
    @abstractmethod
    def format_blocks(self, record: LogRecord) -> Sequence[Block | None]:
        pass

    def get_env(self, config: LogConfig, record: LogRecord) -> str | None:
        dynamic_env: str | None = getattr(record, "environment", None)
        if dynamic_env is not None:
            return dynamic_env
        if config.environment is not None:
            return config.environment
        return None

    def get_service(self, config: LogConfig, record: LogRecord) -> str | None:
        dynamic_service: str | None = getattr(record, "service", None)
        if dynamic_service is not None:
            return dynamic_service
        if config.service is not None:
            return config.service
        return None

    def construct_header(self, record: LogRecord, config: LogConfig, icon: str | None, level: str) -> HeaderBlock:
        service: str | None = self.get_service(config=config, record=record)
        header_msg: str
        if icon is not None:
            header_msg = f"{icon} "
        header_msg += level
        if config.service is not None:
            header_msg += f" | {service}"
        else:
            header_msg += f" | {record.name}"

        return HeaderBlock(text=PlainTextObject(text=header_msg))

    def construct_context(self, config: LogConfig, env: str | None, service: str | None) -> ContextBlock | None:
        if config.context != []:
            context_msg = ", ".join(config.context)
            return ContextBlock(elements=[MarkdownTextObject(text=context_msg)])

        if env is not None and service is not None:
            return ContextBlock(elements=[MarkdownTextObject(text=f":point_right: {env}, {service}")])
        if env is None:
            return ContextBlock(elements=[MarkdownTextObject(text=f":point_right: {env}")])
        if service is None:
            return ContextBlock(elements=[MarkdownTextObject(text=f":point_right: {service}")])

        return None

    def format(self, record: LogRecord) -> str:  # noqa: A003 (allow method name "format")
        maybe_blocks: Sequence[Block | None] = self.format_blocks(record=record)
        blocks: Sequence[Block] = [b for b in maybe_blocks if b is not None]
        str_blocks: str = json.dumps([block.to_dict() for block in blocks])
        log.debug("str_blocks: %s", str_blocks)
        return str_blocks


@define
class NoDesign(MessageDesign):
    def format_blocks(self, record: LogRecord) -> Sequence[Block | None]:
        return [SectionBlock(text=PlainTextObject(text=record.getMessage()))]


@define
class MinimalDesign(MessageDesign):
    config: FormatConfig

    def format_blocks(self, record: LogRecord) -> Sequence[Block | None]:
        level = record.levelname
        message = record.getMessage()
        icon = self.config.emojis.get(record.levelno)

        header: HeaderBlock = self.construct_header(record=record, config=self.config, icon=icon, level=level)

        body = SectionBlock(text=MarkdownTextObject(text=message))
        default_blocks: Sequence[Block] = [
            header,
            body,
        ]

        return default_blocks


@define
class RichDesign(MessageDesign):
    config: FormatConfig

    def format_blocks(self, record: LogRecord) -> Sequence[Block | None]:
        level = record.levelname
        message = record.getMessage()
        icon = self.config.emojis.get(record.levelno)

        env: str | None = self.get_env(config=self.config, record=record)
        service: str | None = self.get_service(config=self.config, record=record)

        header: HeaderBlock = self.construct_header(record=record, config=self.config, icon=icon, level=level)
        context: ContextBlock | None = self.construct_context(config=self.config, env=env, service=service)
        body = SectionBlock(text=MarkdownTextObject(text=message))

        error: SectionBlock | None = None
        if record.exc_info is not None:
            error = SectionBlock(text=MarkdownTextObject(text=f"```{record.exc_text}```"))

        dynamic_extra_fields = getattr(record, "extra_fields", {})
        all_extra_fields = {**self.config.extra_fields, **dynamic_extra_fields}
        fields: SectionBlock | None = None
        if all_extra_fields != {}:
            fields = SectionBlock(
                fields=[MarkdownTextObject(text=f"*{key}*\n{value}") for key, value in all_extra_fields.items()]
            )

        maybe_blocks: Sequence[Block | None] = [
            header,
            context,
            DividerBlock(),
            body,
            error,
            DividerBlock(),
            fields,
        ]

        return maybe_blocks


class SlackFormatter(logging.Formatter):
    design: MessageDesign
    config: FormatConfig | None

    def __init__(self, design: MessageDesign, config: FormatConfig | None = None) -> None:
        super().__init__()
        self.design = design
        self.config = config

    @classmethod
    def plain(cls, config: FormatConfig | None = None) -> "SlackFormatter":
        return cls(design=NoDesign(), config=config)

    @classmethod
    def minimal(cls, config: FormatConfig) -> "SlackFormatter":
        return cls(design=MinimalDesign(config), config=config)

    @classmethod
    def default(cls, config: FormatConfig) -> "SlackFormatter":
        return cls(design=RichDesign(config), config=config)

    def format(self, record: LogRecord) -> str:  # noqa: A003 (allow method name "format")
        super().format(record)
        return self.design.format(record)


class SlackFilter(logging.Filter):
    config: FilterConfig

    def __init__(self, config: FilterConfig | None) -> None:
        self.config = config if config is not None else FilterConfig()
        super().__init__()

    @classmethod
    def filter_by_fields(
        cls, fields: dict[str, str], filter_type: FilterType = FilterType.AnyAllowList
    ) -> "SlackFilter":
        return cls(FilterConfig(extra_fields=fields, filter_type=filter_type, use_regex=False))

    @classmethod
    def filter_by_fields_regex(
        cls, fields: dict[str, str], filter_type: FilterType = FilterType.AnyAllowList
    ) -> "SlackFilter":
        return cls(FilterConfig(extra_fields=fields, filter_type=filter_type, use_regex=True))

    @classmethod
    def hide_by_fields(cls, fields: dict[str, str], filter_type: FilterType = FilterType.AnyDenyList) -> "SlackFilter":
        return cls(FilterConfig(extra_fields=fields, filter_type=filter_type, use_regex=False))

    @classmethod
    def hide_by_fields_regex(
        cls, fields: dict[str, str], filter_type: FilterType = FilterType.AnyDenyList
    ) -> "SlackFilter":
        return cls(FilterConfig(extra_fields=fields, filter_type=filter_type, use_regex=True))

    def match_filter(self, cond_list: list[bool]) -> bool:
        match self.config.filter_type:
            case FilterType.AnyAllowList:
                res = any(cond_list)
            case FilterType.AllAllowList:
                res = all(cond_list)
            case FilterType.AnyDenyList:
                res = not any(cond_list)
            case FilterType.AllDenyList:
                res = not all(cond_list)
        log.debug("final result (%s): res(%s) = %s", self.config.filter_type, res, cond_list)
        return res

    def regex_filter_config(self, service_config: LogConfig) -> bool:
        import re

        res_list = []
        if self.config.service is not None:
            regex = self.config.service
            haystack = service_config.service if service_config.service is not None else ""
            regex_match = re.search(regex, haystack)
            res_list.append(regex_match is not None)
        if self.config.environment is not None:
            regex = self.config.environment
            haystack = service_config.environment if service_config.environment is not None else ""
            regex_match = re.search(regex, haystack)
            res_list.append(regex_match is not None)
        if self.config.context != []:
            regex_list = self.config.context
            haystack_list = service_config.context if service_config.context != [] else []
            for haystack in haystack_list:
                for regex in regex_list:
                    regex_match = re.search(regex, haystack)
                    res_list.append(regex_match is not None)
        for field_key in self.config.extra_fields:
            filter_element = service_config.extra_fields.get(field_key)
            if filter_element is None:
                res_list.append(False)
            else:
                regex = self.config.extra_fields[field_key]
                haystack = filter_element
                regex_match = re.search(regex, haystack)
                log.debug("regex filter with regex = %s, haystack = %s", regex, filter_element)
                res_list.append(regex_match is not None)

        return self.match_filter(res_list)

    def filter_config(self, service_config: LogConfig) -> bool:
        res_list = []
        if self.config.service is not None:
            res_list.append(service_config.service == self.config.service)
        if self.config.environment is not None:
            res_list.append(service_config.environment == self.config.environment)
        if self.config.context != []:
            res_list.extend(
                filter_context == service_context
                for filter_context in self.config.context
                for service_context in service_config.context
            )
        res_list.extend(f in service_config.extra_fields.items() for f in self.config.extra_fields.items())

        return self.match_filter(res_list)

    def filter(self, record: LogRecord) -> bool:
        log_filters = getattr(record, "filter", None)
        if log_filters is None:
            return True

        extra_fields = log_filters.get("extra_fields", {})
        log.debug("EXTRA FIELDS: %s", extra_fields)
        rconfig: FilterConfig = FilterConfig(
            service=log_filters.get("service", None),
            environment=log_filters.get("environment", None),
            context=log_filters.get("context", []),
            extra_fields=log_filters.get("extra_fields", {}),
        )
        if self.config.use_regex is True:
            return self.regex_filter_config(service_config=rconfig)

        return self.filter_config(service_config=rconfig)


@define
class DummyClient(AsyncWebhookClient):
    url: str = ""

    async def send(  # noqa: PLR0913 (allow many arguments here)
        self,
        *,
        text: str | None = None,
        attachments: Sequence[dict[str, Any] | Attachment] | None = None,  # noqa: ARG002
        blocks: Sequence[dict[str, Any] | Block] | None = None,
        response_type: str | None = None,  # noqa: ARG002
        replace_original: bool | None = None,  # noqa: ARG002
        delete_original: bool | None = None,  # noqa: ARG002
        unfurl_links: bool | None = None,  # noqa: ARG002
        unfurl_media: bool | None = None,  # noqa: ARG002
        metadata: dict[str, Any] | None = None,  # noqa: ARG002
        headers: dict[str, str] | None = None,  # noqa: ARG002
    ) -> WebhookResponse:
        assert text is not None or blocks is not None  # noqa: S101 (allow assert here)

        t: str
        if text is None and blocks is not None:
            res = []
            for block in blocks:
                assert isinstance(block, Block)  # noqa: S101 (allow assert here)
                res.append(block.to_dict())
            t = json.dumps({"blocks": res})
        else:
            t = json.dumps({"text": str(text)})

        log.debug(t)
        return WebhookResponse(url="", status_code=200, body="ok", headers={})


class SlackHandler(logging.Handler):
    client: AsyncWebhookClient
    config: LogConfig

    def __init__(self, client: AsyncWebhookClient, config: LogConfig | None) -> None:
        self.client = client
        self.config = config if config is not None else LogConfig()
        super().__init__()

    @classmethod
    def from_webhook(cls, webhook_url: str) -> "SlackHandler":
        return cls(client=AsyncWebhookClient(webhook_url), config=LogConfig())

    @classmethod
    def dummy(cls) -> "SlackHandler":
        return cls(client=DummyClient(), config=LogConfig())

    async def send_text_via_webhook(self, text: str) -> str:
        response = await self.client.send(text=text)
        if response.status_code != HTTPOk().status_code or response.body != "ok":
            raise SendError(code=response.status_code, msg=response.body)
        return str(response.body)

    async def send_blocks_via_webhook(self, blocks: str) -> str:
        block_seq = Block.parse_all(json.loads(blocks))
        response = await self.client.send(blocks=block_seq)
        if response.status_code != HTTPOk().status_code or response.body != "ok":
            raise SendError(code=response.status_code, msg=response.body)
        return str(response.body)

    def emit(self, record: LogRecord) -> None:
        try:
            formatted_message = self.format(record)
            if isinstance(self.formatter, SlackFormatter):
                asyncio.run(self.send_blocks_via_webhook(blocks=formatted_message))
            else:
                asyncio.run(self.send_text_via_webhook(text=formatted_message))

        except Exception:
            log.exception("Couldn't send message to webhook!")
            self.handleError(record)

    def handle(self, record: LogRecord) -> bool:
        # This pre-filters the messages with the Slack Filters
        if isinstance(self.formatter, SlackFormatter) and self.formatter.config is not None:
            combined_config: LogConfig = structure(
                {
                    **asdict(self.formatter.config),
                    **{k: v for k, v in asdict(self.config).items() if v is not None},  # overwrite non None values
                },
                LogConfig,
            )
            log.debug("handler config: %s", self.config)
            log.debug("formatter config: %s", self.formatter.config)
            log.debug("combined config: %s", combined_config)
            for sf in self.filters:
                if isinstance(sf, SlackFilter):
                    res = True
                    if sf.config.use_regex is True:
                        res = sf.regex_filter_config(service_config=combined_config)
                    else:
                        res = sf.filter_config(service_config=combined_config)
                    if res is False:
                        return False

        return super().handle(record)
