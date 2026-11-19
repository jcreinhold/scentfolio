"""Configure Pydantic AI for the fragrance model requests."""

import os
from dataclasses import dataclass
from functools import partial
from typing import Literal

from httpx2 import URL, AsyncClient, HTTPError, InvalidURL, Request, Timeout
from pydantic_ai import Agent
from pydantic_ai.capabilities import Citations, WebSearch
from pydantic_ai.exceptions import (
    AgentRunError,
    ModelHTTPError,
    UnexpectedModelBehavior,
    UserError,
)
from pydantic_ai.messages import ModelResponse, TextPart, WebCitationSource
from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openai_compatible import OpenAICompatibleProvider


class LookupError(Exception):
    """An AI operation failed with a message safe to show to the user."""


_ANTHROPIC_BASE_URL = "https://api.anthropic.com"
_OPENAI_BASE_URL = "https://api.openai.com/v1"
_ANTHROPIC_OPUS = "claude-opus-5-5"
_ANTHROPIC_MODELS = {
    "lookup": _ANTHROPIC_OPUS,
    "enrich": "claude-haiku-5-5",
    "classify": _ANTHROPIC_OPUS,
}
_NO_SEARCH = "Web search is unavailable. Omit unknown details."
_UNREADABLE = "The language model returned an unreadable response."


@dataclass(frozen=True)
class _ModelConfig:
    provider: str
    model: str
    base_url: str
    key: str | None


def _setting(name: str) -> str | None:
    return os.getenv(name, "").strip() or None


def _web_url(value: str) -> URL | None:
    try:
        url = URL(value)
    except InvalidURL, ValueError:
        return None
    if url.scheme in {"http", "https"} and url.host and not url.userinfo:
        return url
    return None


def _config(task: str) -> _ModelConfig:
    provider = (_setting("SCENTFOLIO_LLM_PROVIDER") or "anthropic").lower()
    if provider not in {"anthropic", "openai", "openai-compatible"}:
        raise LookupError("SCENTFOLIO_LLM_PROVIDER is not supported.")

    base = _setting("SCENTFOLIO_LLM_BASE_URL")
    if base:
        url = _web_url(base)
        if url is None or "?" in base or "#" in base:
            raise LookupError(
                "SCENTFOLIO_LLM_BASE_URL must be an HTTP or HTTPS API base URL."
            )
        base = str(url).rstrip("/")

    model = _setting("SCENTFOLIO_LLM_MODEL")
    key = _setting("SCENTFOLIO_LLM_API_KEY")
    default_base, fallback_key = (
        (_ANTHROPIC_BASE_URL, "ANTHROPIC_API_KEY")
        if provider == "anthropic"
        else (_OPENAI_BASE_URL, "OPENAI_API_KEY")
    )
    base = base or default_base
    if base == default_base:
        key = key or _setting(fallback_key)
        if not key:
            raise LookupError(f"Set SCENTFOLIO_LLM_API_KEY or {fallback_key}.")
    elif provider != "openai-compatible" and not key:
        raise LookupError(
            "Set SCENTFOLIO_LLM_API_KEY when overriding the provider URL."
        )

    if provider == "anthropic":
        model = model or _ANTHROPIC_MODELS[task]
    elif not model:
        raise LookupError("Set SCENTFOLIO_LLM_MODEL for the configured provider.")
    return _ModelConfig(provider, model, base, key)


def _model(config: _ModelConfig, http_client: AsyncClient) -> Model:
    options = {
        "base_url": config.base_url,
        "api_key": config.key,
        "http_client": http_client,
    }
    if config.provider == "anthropic":
        return AnthropicModel(config.model, provider=AnthropicProvider(**options))
    if config.provider == "openai":
        return OpenAIResponsesModel(config.model, provider=OpenAIProvider(**options))
    if config.base_url == _OPENAI_BASE_URL:
        return OpenAIChatModel(config.model, provider=OpenAIProvider(**options))
    provider = OpenAICompatibleProvider(
        "scentfolio-compatible",
        profile=OpenAIModelProfile(openai_chat_supports_max_completion_tokens=False),
        **options,
    )
    return OpenAIChatModel(config.model, provider=provider)


async def _isolate_gateway_headers(request: Request, *, config: _ModelConfig) -> None:
    header_setting = (
        "ANTHROPIC_CUSTOM_HEADERS"
        if config.provider == "anthropic"
        else "OPENAI_CUSTOM_HEADERS"
    )
    # Match the SDK's newline-delimited name: value format.
    for line in os.getenv(header_setting, "").split("\n"):
        name, colon, _ = line.partition(":")
        if colon:
            request.headers.pop(name.strip(), None)
    for name in ("OpenAI-Organization", "OpenAI-Project", "X-Api-Key"):
        request.headers.pop(name, None)
    if config.key is None:
        # Pydantic AI supplies the OpenAI SDK a placeholder for anonymous APIs.
        request.headers.pop("Authorization", None)
    else:
        request.headers["Authorization"] = f"Bearer {config.key}"


def _sources(response: ModelResponse) -> list[str]:
    urls: dict[str, None] = {}
    for part in response.parts:
        if isinstance(part, TextPart):
            for citation in part.citations or ():
                for source in citation.sources:
                    if isinstance(source, WebCitationSource):
                        url = _web_url(source.url)
                        if url is not None:
                            urls[str(url)] = None
    return list(urls)


async def _run(
    config: _ModelConfig,
    system: str,
    prompt: str,
    *,
    max_tokens: int,
    search_enabled: bool,
) -> tuple[str, list[str]]:
    default_base = (
        _ANTHROPIC_BASE_URL if config.provider == "anthropic" else _OPENAI_BASE_URL
    )
    hooks = None
    if config.base_url != default_base:
        hooks = {"request": [partial(_isolate_gateway_headers, config=config)]}
    async with AsyncClient(
        timeout=Timeout(120, connect=10), follow_redirects=False, event_hooks=hooks
    ) as http_client:
        settings = {"max_tokens": max_tokens}
        if config.provider == "openai":
            settings["openai_store"] = False
        elif (
            config.provider == "anthropic"
            and config.model in _ANTHROPIC_MODELS.values()
        ):
            settings["anthropic_effort"] = "low"
            if config.model == _ANTHROPIC_OPUS:
                # Opus 5.5 shares this allowance between mandatory thinking and text.
                settings["max_tokens"] = max(max_tokens, 4096)
        agent = Agent(
            _model(config, http_client),
            instructions=system,
            model_settings=settings,
            capabilities=[WebSearch(), Citations()] if search_enabled else [],
        )
        result = await agent.run(prompt)
        text = result.output
        if not isinstance(text, str) or not text.strip():
            raise LookupError("The language model returned no text.")
        return text, _sources(result.response) if search_enabled else []


async def complete(
    system: str,
    prompt: str,
    *,
    max_tokens: int,
    task: Literal["lookup", "enrich", "classify"],
    search: str | None = None,
) -> tuple[str, list[str]]:
    """Run a request with the configured provider.

    Returns:
        Model text and web URLs cited by the provider.

    Raises:
        LookupError: Configuration, transport, or model output prevented completion.
    """
    config = _config(task)
    search_enabled = search is not None and (
        (config.provider == "anthropic" and task in {"lookup", "classify"})
        or (config.provider == "openai" and task == "lookup")
    )
    if search is not None:
        system += "\n\n" + (search if search_enabled else _NO_SEARCH)

    try:
        return await _run(
            config,
            system,
            prompt,
            max_tokens=max_tokens,
            search_enabled=search_enabled,
        )
    except ModelHTTPError as error:
        raise LookupError(
            f"Language model request failed (HTTP {error.status_code})."
        ) from None
    except UnexpectedModelBehavior:
        raise LookupError(_UNREADABLE) from None
    except UserError:
        raise LookupError(
            "Check that SCENTFOLIO_LLM_MODEL supports this request."
        ) from None
    except AgentRunError, HTTPError, InvalidURL, ValueError:
        raise LookupError("The language model request failed.") from None
