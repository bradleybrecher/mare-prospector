"""Thin wrapper around the official `google-genai` SDK.

Why this file exists:
- One place to enforce brand-safe defaults (temperature, safety, model).
- One place to inject the MaRe brand system prompt on every call.
- Keeps call sites (outreach, content) free of SDK boilerplate.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from mare.brand import BRAND_SYSTEM_PROMPT
from mare.config import Settings

log = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    text: str
    model: str
    prompt_tokens: int | None
    output_tokens: int | None


class GeminiClient:
    """Brand-aware Gemini client.

    Usage:
        client = GeminiClient.from_env()
        result = client.generate("Write a one-line tagline for a head spa.")
        print(result.text)
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = genai.Client(api_key=settings.gemini_api_key)

    @classmethod
    def from_env(cls) -> "GeminiClient":
        return cls(Settings.load())

    @property
    def reasoning_model(self) -> str:
        """Name of the model used for reasoning-heavy tasks."""
        return self._settings.gemini_reasoning_model

    @property
    def raw_client(self) -> genai.Client:
        """Underlying google-genai Client (for image/video generation paths)."""
        return self._client

    def generate(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        response_schema: Any | None = None,
        json_mode: bool = False,
        model: str | None = None,
        use_reasoning_model: bool = False,
    ) -> GenerationResult:
        """Run a single-turn generation.

        `system_instruction` is prepended to the always-on MaRe brand prompt.
        Pass `response_schema` to force strict, schema-validated JSON.
        Pass `json_mode=True` (without a schema) to force free-form valid JSON.
        """
        system = BRAND_SYSTEM_PROMPT
        if system_instruction:
            system = f"{BRAND_SYSTEM_PROMPT}\n\n---\n{system_instruction}"

        config_kwargs: dict[str, Any] = {
            "system_instruction": system,
            "temperature": temperature if temperature is not None else self._settings.gemini_temperature,
            "max_output_tokens": max_output_tokens or self._settings.gemini_max_output_tokens,
        }
        if response_schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema
        elif json_mode:
            # JSON mode without a schema: Gemini guarantees syntactically valid
            # JSON but won't enforce structure. Use when the shape is too loose
            # (mixed-type fields, arrays of free dicts) to pin down in a schema.
            config_kwargs["response_mime_type"] = "application/json"

        primary_model = (
            model
            or (self._settings.gemini_reasoning_model if use_reasoning_model else None)
            or self._settings.gemini_model
        )
        fallback_model = (
            self._settings.gemini_fallback_model
            if self._settings.gemini_fallback_model
            and self._settings.gemini_fallback_model != primary_model
            else None
        )
        config = types.GenerateContentConfig(**config_kwargs)
        response, effective_model = self._generate_with_resilience(
            primary_model=primary_model,
            fallback_model=fallback_model,
            contents=prompt,
            config=config,
        )

        usage = getattr(response, "usage_metadata", None)
        return GenerationResult(
            text=(response.text or "").strip(),
            model=effective_model,
            prompt_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
            output_tokens=getattr(usage, "candidates_token_count", None) if usage else None,
        )

    def _generate_with_resilience(
        self,
        *,
        primary_model: str,
        fallback_model: str | None,
        contents: str,
        config: types.GenerateContentConfig,
        max_transient_retries: int = 2,
    ) -> tuple[Any, str]:
        """Call the API with two safety nets:

        1. Transient 5xx / 503 UNAVAILABLE -> exponential retry (2 attempts).
        2. 429 RESOURCE_EXHAUSTED on the reasoning model -> one automatic
           fallback to the default (cheaper) model. This keeps the pipeline
           flowing when free-tier Pro quota is empty.
        """
        models_to_try: list[str] = [primary_model]
        if fallback_model and fallback_model != primary_model:
            models_to_try.append(fallback_model)

        last_exc: Exception | None = None
        for attempt_model in models_to_try:
            for retry in range(max_transient_retries + 1):
                try:
                    response = self._client.models.generate_content(
                        model=attempt_model,
                        contents=contents,
                        config=config,
                    )
                    if retry > 0 or attempt_model != primary_model:
                        log.info(
                            "Gemini call succeeded on model=%s (retry=%d, primary=%s)",
                            attempt_model, retry, primary_model,
                        )
                    return response, attempt_model
                except genai_errors.ServerError as exc:
                    last_exc = exc
                    if retry >= max_transient_retries:
                        break
                    backoff = 2 ** retry
                    log.warning(
                        "Gemini %s transient error (%s). Retrying in %ds.",
                        attempt_model, exc.__class__.__name__, backoff,
                    )
                    time.sleep(backoff)
                except genai_errors.ClientError as exc:
                    last_exc = exc
                    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
                    if status == 429 and attempt_model != models_to_try[-1]:
                        log.warning(
                            "Gemini %s quota exhausted (429). Falling back to %s.",
                            attempt_model, models_to_try[-1],
                        )
                        break  # try next model
                    raise  # other 4xx errors are user-fixable; don't retry or fall back.

        assert last_exc is not None
        raise last_exc
