from __future__ import annotations

import hashlib
import json
from datetime import date, datetime

from .cache import BriefCache
from .config import AppConfig
from .demo_data import build_demo_context, get_demo_context_signature
from .llm import (
    AnthropicBriefProvider,
    BriefProvider,
    DeterministicBriefProvider,
    OpenAIBriefProvider,
    build_brief_response,
    trim_brief_to_limit,
)
from .schemas import BriefContext, BriefRequest, BriefResponse


class DemandBriefService:
    def __init__(self, config: AppConfig, cache: BriefCache) -> None:
        self._config = config
        self._cache = cache
        self._fallback_provider = DeterministicBriefProvider()

    def _resolve_provider(self) -> tuple[BriefProvider, str]:
        provider = self._config.llm_provider
        if provider == "anthropic" and self._config.anthropic_api_key:
            return AnthropicBriefProvider(self._config.anthropic_api_key, self._config.request_timeout_seconds), "anthropic"
        if provider == "openai" and self._config.openai_api_key:
            return OpenAIBriefProvider(self._config.openai_api_key, self._config.request_timeout_seconds), "openai"
        if provider == "auto":
            if self._config.anthropic_api_key:
                return AnthropicBriefProvider(self._config.anthropic_api_key, self._config.request_timeout_seconds), "anthropic"
            if self._config.openai_api_key:
                return OpenAIBriefProvider(self._config.openai_api_key, self._config.request_timeout_seconds), "openai"
        return self._fallback_provider, "deterministic"

    def _build_context(self, request: BriefRequest) -> BriefContext:
        brief_date = request.brief_date or date.today()
        return build_demo_context(
            brief_date=brief_date,
            max_urgent=min(request.max_urgent_skus, self._config.max_brief_skus),
            max_overstock=min(request.max_overstock_skus, self._config.max_brief_skus),
            max_watch=min(request.max_watch_skus, self._config.max_brief_skus),
        )

    def _cache_key(self, context: BriefContext, provider_name: str) -> str:
        cache_payload = {
            "brief_date": context.brief_date.isoformat(),
            "model_version": self._config.model_version,
            "provider": provider_name,
            "data_signature": get_demo_context_signature(),
        }
        digest = hashlib.sha256(json.dumps(cache_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        return f"brief:{digest}"

    @staticmethod
    def _context_for_cache(context: BriefContext) -> dict:
        if hasattr(context, "model_dump"):
            return context.model_dump(mode="json")
        return json.loads(context.json())

    def generate_weekly_brief(self, request: BriefRequest) -> BriefResponse:
        context = self._build_context(request)
        provider, provider_name = self._resolve_provider()
        cache_key = self._cache_key(context, provider_name)

        if not request.force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                cached_context = BriefContext.parse_obj(cached.payload["context"])
                return build_brief_response(
                    brief_text=cached.payload["brief_text"],
                    context=cached_context,
                    model_version=cached.payload["model_version"],
                    provider_name=cached.payload["provider"],
                    cache_hit=True,
                )

        brief_text, actual_provider_name = self._generate_with_fallback(provider, context, provider_name)
        cache_key = self._cache_key(context, actual_provider_name)
        response = build_brief_response(
            brief_text=brief_text,
            context=context,
            model_version=self._config.model_version,
            provider_name=actual_provider_name,
            cache_hit=False,
        )
        self._cache.put(
            cache_key,
            {
                "brief_text": response.brief_text,
                "context": self._context_for_cache(response.context),
                "model_version": response.model_version,
                "provider": response.provider,
            },
        )
        return response

    def _generate_with_fallback(
        self, provider: BriefProvider, context: BriefContext, provider_name: str
    ) -> tuple[str, str]:
        attempts = 3 if provider_name != "deterministic" else 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                brief_text = provider.generate(context, self._config.model_version)
                return trim_brief_to_limit(brief_text), provider_name
            except Exception as exc:  # noqa: BLE001 - controlled fallback boundary
                last_error = exc
                if provider_name == "deterministic":
                    break
                if attempt < attempts - 1:
                    continue
        if last_error is not None:
            fallback_text = self._fallback_provider.generate(context, self._config.model_version)
            return (
                trim_brief_to_limit(
                    fallback_text
                    + "\n\nFallback note: remote provider unavailable; generated locally from validated demo data."
                ),
                "deterministic-fallback",
            )
        return trim_brief_to_limit(self._fallback_provider.generate(context, self._config.model_version)), "deterministic"
