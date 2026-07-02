import json
import logging
import re
from typing import Dict, Optional

import requests

# Provider SDKs (openai, anthropic, google.genai) are imported lazily inside the methods
# that use them — importing all three at module load added ~1.5s to server startup
# (google.genai alone ~0.7s), even when only one provider is used.

from libriscribe.settings import Settings
from libriscribe.utils import structured_output
from libriscribe.utils.cost_tracker import CostTracker
from libriscribe.utils.file_utils import extract_json_from_markdown, parse_llm_json
from libriscribe.utils.token_utils import estimate_tokens
from libriscribe.utils.model_routing import (
    ModelRoute,
    build_fallback_route_chain,
    get_default_model_for_provider,
    normalize_fallback_chain,
    parse_fallback_chain_string,
)

logger = logging.getLogger(__name__)


# Tokens that identify a "the structured-output param is unsupported" failure, so we can retry the
# same call WITHOUT the schema instead of failing. Lets structured output be universal + safe.
_SCHEMA_ERROR_TOKENS = (
    "response_format", "json_schema", "response_mime_type", "response_schema", "output_config",
)


def _is_schema_error(exc: Exception) -> bool:
    """True if an exception looks like the provider/SDK rejecting the structured-output param."""
    if isinstance(exc, TypeError):  # SDK too old for the kwarg
        return True
    msg = f"{getattr(exc, 'message', '')} {exc}".lower()
    return any(tok in msg for tok in _SCHEMA_ERROR_TOKENS)


def _call_or_degrade(with_schema, without_schema):
    """Run ``with_schema``; if it fails specifically because structured output is unsupported,
    fall back to ``without_schema``. Other errors propagate to the normal fallback loop. Servers
    that SILENTLY ignore the schema need no handling — their output is still parsed downstream."""
    try:
        return with_schema()
    except Exception as exc:  # noqa: BLE001 — classify then re-raise non-schema errors
        if _is_schema_error(exc):
            logger.info("Structured output unsupported (%s); retrying without schema.", exc)
            return without_schema()
        raise

httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)


class RecoverableLLMError(Exception):
    def __init__(self, failure_type: str, message: str):
        super().__init__(message)
        self.failure_type = failure_type


class LLMClient:
    """Unified LLM client for multiple providers with simple fallback routing."""

    def __init__(self, llm_provider: str):
        self.settings = Settings()
        self.llm_provider = llm_provider
        self._client_cache: Dict[str, object] = {}
        self.client = self._get_client_for_provider(llm_provider)
        self.default_model = self._get_default_model_for_provider(llm_provider)
        self.model = self.default_model
        self.cost_tracker = CostTracker()
        self.request_fallback_chain: Optional[list[str]] = None

    def _get_client_for_provider(self, provider: str):
        if provider in self._client_cache:
            return self._client_cache[provider]

        if provider == "openrouter":
            if not self.settings.openrouter_api_key:
                raise ValueError("OpenRouter API key is not set.")
            from openai import OpenAI
            client = OpenAI(
                api_key=self.settings.openrouter_api_key,
                base_url=self.settings.openrouter_base_url,
            )
        elif provider == "openai":
            if not self.settings.openai_api_key:
                raise ValueError("OpenAI API key is not set.")
            from openai import OpenAI
            client = OpenAI(api_key=self.settings.openai_api_key)
        elif provider == "claude":
            if not self.settings.claude_api_key:
                raise ValueError("Claude API key is not set.")
            import anthropic
            client = anthropic.Anthropic(api_key=self.settings.claude_api_key)
        elif provider == "google_ai_studio":
            if not self.settings.google_ai_studio_api_key:
                raise ValueError("Google AI Studio API key is not set.")
            from google import genai
            client = genai.Client(api_key=self.settings.google_ai_studio_api_key)
        elif provider == "deepseek":
            if not self.settings.deepseek_api_key:
                raise ValueError("DeepSeek API key is not set.")
            client = None
        elif provider == "mistral":
            if not self.settings.mistral_api_key:
                raise ValueError("Mistral API key is not set.")
            client = None
        elif provider == "local":
            # Local / OpenAI-compatible server (LM Studio, Ollama, llama.cpp, ...).
            # base_url points at localhost, so requests never leave the machine.
            from libriscribe.utils.model_routing import normalize_openai_base_url
            from openai import OpenAI

            base_url = normalize_openai_base_url(self.settings.local_base_url)
            if not base_url:
                raise ValueError("Local LLM base URL is not set.")
            client = OpenAI(
                api_key=self.settings.local_api_key or "not-needed",
                base_url=base_url,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        self._client_cache[provider] = client
        return client

    def _get_default_model_for_provider(self, provider: str) -> str:
        return get_default_model_for_provider(provider, self.settings)

    def set_model(self, model_name: str):
        self.model = model_name

    def reset_model(self):
        self.model = self.default_model

    def set_fallback_chain(self, fallback_chain: Optional[list[str]]):
        if fallback_chain is None:
            self.request_fallback_chain = None
            return
        self.request_fallback_chain = normalize_fallback_chain(fallback_chain)

    def _get_active_fallback_chain(self) -> list[str]:
        if self.request_fallback_chain is not None:
            return self.request_fallback_chain
        return parse_fallback_chain_string(self.settings.fallback_chain)

    def _prepare_prompt(self, prompt: str, language: str) -> str:
        if (
            "IMPORTANT: The content should be written entirely in" not in prompt
            and language != "English"
        ):
            return prompt + f"\n\nIMPORTANT: Generate the response in {language}."
        return prompt

    def _get_status_code(self, exc: Exception) -> Optional[int]:
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int):
            return status_code

        response = getattr(exc, "response", None)
        if response is not None:
            response_status = getattr(response, "status_code", None)
            if isinstance(response_status, int):
                return response_status

        return None

    def _classify_exception(self, exc: Exception) -> str:
        if isinstance(exc, RecoverableLLMError):
            return exc.failure_type

        if isinstance(exc, requests.Timeout):
            return "timeout"

        status_code = self._get_status_code(exc)
        if status_code == 429:
            return "rate_limit"
        if status_code and 500 <= status_code < 600:
            return "provider_server_error"

        message = str(exc).lower()
        if "timeout" in message or "timed out" in message:
            return "timeout"
        if (
            "429" in message
            or "rate limit" in message
            or "too many requests" in message
        ):
            return "rate_limit"
        if "api key is not set" in message:
            return "provider_not_configured"
        if "500" in message or "502" in message or "503" in message or "504" in message:
            return "provider_server_error"

        return "unhandled_error"

    def _should_retry_same_route(self, failure_type: str) -> bool:
        return failure_type in {"timeout", "rate_limit", "provider_server_error"}

    def _should_fallback(self, failure_type: str) -> bool:
        return failure_type in {
            "timeout",
            "rate_limit",
            "provider_server_error",
            "empty_response",
            "invalid_json_after_repair",
            "provider_not_configured",
        }

    def _log_usage(self, provider: str, model: str, prompt: str, response_text: str):
        input_tokens = estimate_tokens(prompt)
        output_tokens = estimate_tokens(response_text)
        cost = self.cost_tracker.calculate_cost(
            f"{provider}/{model}",
            int(input_tokens),
            int(output_tokens),
        )
        self.cost_tracker.log_usage(
            provider,
            model,
            "generate_content",
            int(input_tokens),
            int(output_tokens),
            cost,
        )

    def _request_with_fallback(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        language: str = "English",
        require_valid_json: bool = False,
        system_prompt: Optional[str] = None,
        json_schema: Optional[dict] = None,
    ) -> str:
        prepared_prompt = self._prepare_prompt(prompt, language)
        routes = build_fallback_route_chain(
            primary_provider=self.llm_provider,
            primary_model=self.model or self.default_model,
            fallback_chain=self._get_active_fallback_chain(),
            settings=self.settings,
        )
        last_error: Optional[Exception] = None

        for route_index, route in enumerate(routes):
            for attempt in range(1, 3):
                try:
                    response_text = self._generate_once(
                        route,
                        prepared_prompt,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        system_prompt=system_prompt,
                        json_schema=json_schema,
                    )
                    if not response_text or not response_text.strip():
                        raise RecoverableLLMError(
                            "empty_response",
                            f"{route.label} returned an empty response.",
                        )

                    if require_valid_json:
                        # Validate with the tolerant parser (fenced ```json, plain fences, BARE
                        # JSON, or a reasoning preamble). Structured output and clean instruct
                        # models return BARE JSON — the old fence-only check rejected that and sent
                        # it to "repair", which then failed to an empty string.
                        json_data = parse_llm_json(response_text)
                        if json_data is None:
                            repair_prompt = (
                                "You are a helpful AI that only returns valid JSON. "
                                "Fix the following broken JSON:\n\n"
                                f"```json\n{response_text}\n```"
                            )
                            repaired_response = self._generate_once(
                                route,
                                repair_prompt,
                                max_tokens=max_tokens,
                                temperature=0.2,
                            )
                            json_data = parse_llm_json(repaired_response) if repaired_response else None
                            if json_data is None:
                                raise RecoverableLLMError(
                                    "invalid_json_after_repair",
                                    f"{route.label} returned invalid JSON after repair.",
                                )
                        # Normalize to fenced JSON so every downstream consumer works — both those
                        # that call extract_json_from_markdown (generation agents) and those that
                        # call parse_llm_json (lore intake) — regardless of what the model emitted.
                        response_text = "```json\n" + json.dumps(json_data, ensure_ascii=False) + "\n```"

                    if route_index > 0:
                        logger.warning(
                            "Fallback succeeded: using %s after previous route failure.",
                            route.label,
                        )
                    return response_text
                except Exception as exc:
                    last_error = exc
                    failure_type = self._classify_exception(exc)
                    logger.warning(
                        "LLM route %s failed on attempt %s (%s): %s",
                        route.label,
                        attempt,
                        failure_type,
                        exc,
                    )

                    if attempt < 2 and self._should_retry_same_route(failure_type):
                        continue

                    has_next_route = route_index < len(routes) - 1
                    if has_next_route and self._should_fallback(failure_type):
                        next_route = routes[route_index + 1]
                        logger.warning(
                            "Falling back from %s to %s due to %s.",
                            route.label,
                            next_route.label,
                            failure_type,
                        )
                        break

                    logger.error(
                        "LLM generation failed for %s with no further fallback available.",
                        route.label,
                    )
                    return ""

        if last_error:
            logger.error(
                "LLM generation failed after exhausting fallback routes: %s", last_error
            )
        return ""

    def _generate_once(
        self,
        route: ModelRoute,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str] = None,
        json_schema: Optional[dict] = None,
    ) -> str:
        provider = route.provider
        model = route.model

        if provider in {"openai", "openrouter", "local"}:
            client = self._get_client_for_provider(provider)
            request_prompt = prompt
            if provider == "openrouter":
                request_prompt = (
                    prompt
                    + "\n\nPlease format any JSON output in markdown code blocks with ```json```"
                )
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": request_prompt})
            base = dict(model=model, messages=messages, max_tokens=max_tokens, temperature=temperature)
            if json_schema:
                rf = structured_output.response_format_openai(json_schema)
                response = _call_or_degrade(
                    lambda: client.chat.completions.create(**base, response_format=rf),
                    lambda: client.chat.completions.create(**base),
                )
            else:
                response = client.chat.completions.create(**base)
            content = (response.choices[0].message.content or "").strip()
            if provider == "openrouter" and "```json" not in content and "{" in content:
                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    content = f"```json\n{json_match.group()}\n```"
            self._log_usage(provider, model, prompt, content)
            return content

        if provider == "claude":
            client = self._get_client_for_provider(provider)
            claude_kwargs = dict(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            if system_prompt:
                claude_kwargs["system"] = system_prompt
            if json_schema:
                output_config = {"format": {"type": "json_schema", "schema": json_schema}}
                response = _call_or_degrade(
                    lambda: client.messages.create(**claude_kwargs, output_config=output_config),
                    lambda: client.messages.create(**claude_kwargs),
                )
            else:
                response = client.messages.create(**claude_kwargs)
            text_content = response.content[0].text.strip()
            self._log_usage(provider, model, prompt, text_content)
            return text_content

        if provider == "google_ai_studio":
            from google.genai import types as google_genai_types
            client = self._get_client_for_provider(provider)
            google_config_kwargs: dict = dict(
                temperature=temperature,
                max_output_tokens=max_tokens,
                thinking_config=google_genai_types.ThinkingConfig(
                    thinking_budget=0,
                ),
            )
            if system_prompt:
                google_config_kwargs["system_instruction"] = system_prompt

            def _google_generate(extra_cfg: dict):
                cfg = google_genai_types.GenerateContentConfig(**google_config_kwargs, **extra_cfg)
                return client.models.generate_content(model=model, contents=prompt, config=cfg)

            if json_schema:
                response = _call_or_degrade(
                    lambda: _google_generate(
                        {"response_mime_type": "application/json", "response_schema": json_schema}
                    ),
                    lambda: _google_generate({}),
                )
            else:
                response = _google_generate({})
            text_response = (response.text or "").strip()
            self._log_usage(provider, model, prompt, text_response)
            return text_response

        if provider == "deepseek":
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.deepseek_api_key}",
            }
            ds_messages = []
            if system_prompt:
                ds_messages.append({"role": "system", "content": system_prompt})
            ds_messages.append({"role": "user", "content": prompt})

            def _deepseek_post(extra: dict):
                data = {
                    "model": model, "messages": ds_messages,
                    "max_tokens": max_tokens, "temperature": temperature, **extra,
                }
                return requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers=headers, json=data, timeout=120,
                )

            if json_schema:  # DeepSeek supports json_object (best-effort), not json_schema
                response = _deepseek_post({"response_format": structured_output.response_format_json_object()})
                if response.status_code >= 400:  # provider rejected the param — retry plain
                    response = _deepseek_post({})
            else:
                response = _deepseek_post({})
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            self._log_usage(provider, model, prompt, content)
            return content

        if provider == "mistral":
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.mistral_api_key}",
            }
            mi_messages = []
            if system_prompt:
                mi_messages.append({"role": "system", "content": system_prompt})
            mi_messages.append({"role": "user", "content": prompt})

            def _mistral_post(extra: dict):
                data = {
                    "model": model, "messages": mi_messages,
                    "max_tokens": max_tokens, "temperature": temperature, **extra,
                }
                return requests.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers=headers, json=data, timeout=120,
                )

            if json_schema:  # Mistral supports OpenAI-style json_schema (strict)
                response = _mistral_post(
                    {"response_format": structured_output.response_format_openai(json_schema)}
                )
                if response.status_code >= 400:  # provider rejected the schema — retry plain
                    response = _mistral_post({})
            else:
                response = _mistral_post({})
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            self._log_usage(provider, model, prompt, content)
            return content

        raise ValueError(f"Unsupported LLM provider: {provider}")

    def generate_content(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        language: str = "English",
        system_prompt: Optional[str] = None,
    ) -> str:
        return self._request_with_fallback(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            language=language,
            require_valid_json=False,
            system_prompt=system_prompt,
        )

    def generate_content_with_json_repair(
        self,
        original_prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        json_schema: Optional[dict] = None,
    ) -> str:
        return self._request_with_fallback(
            prompt=original_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            require_valid_json=True,
            system_prompt=system_prompt,
            json_schema=json_schema,
        )

    def generate_content_streaming(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        language: str = "English",
        system_prompt: Optional[str] = None,
    ):
        """Returns an Iterator[str] that yields text chunks as they are generated.

        Uses the primary provider only (no fallback chain for streaming).
        Falls back to non-streaming if a provider does not support it.
        """
        prepared_prompt = self._prepare_prompt(prompt, language)
        provider = self.llm_provider
        model = self.model or self.default_model

        if provider in {"openai", "openrouter", "local"}:
            client = self._get_client_for_provider(provider)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prepared_prompt})
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return

        if provider == "claude":
            client = self._get_client_for_provider(provider)
            stream_kwargs = dict(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prepared_prompt}],
            )
            if system_prompt:
                stream_kwargs["system"] = system_prompt
            with client.messages.stream(**stream_kwargs) as stream:
                for text in stream.text_stream:
                    yield text
            return

        if provider == "google_ai_studio":
            from google.genai import types as google_genai_types
            client = self._get_client_for_provider(provider)
            stream_config_kwargs: dict = dict(
                temperature=temperature,
                max_output_tokens=max_tokens,
                thinking_config=google_genai_types.ThinkingConfig(
                    thinking_budget=0,
                ),
            )
            if system_prompt:
                stream_config_kwargs["system_instruction"] = system_prompt
            response = client.models.generate_content_stream(
                model=model,
                contents=prepared_prompt,
                config=google_genai_types.GenerateContentConfig(**stream_config_kwargs),
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
            return

        if provider == "deepseek":
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.deepseek_api_key}",
            }
            ds_stream_msgs = []
            if system_prompt:
                ds_stream_msgs.append({"role": "system", "content": system_prompt})
            ds_stream_msgs.append({"role": "user", "content": prepared_prompt})
            data = {
                "model": model,
                "messages": ds_stream_msgs,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
            }
            with requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=120,
                stream=True,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode("utf-8")
                        if line_str.startswith("data: ") and line_str != "data: [DONE]":
                            import json as _json
                            try:
                                chunk_data = _json.loads(line_str[6:])
                                content = chunk_data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content:
                                    yield content
                            except _json.JSONDecodeError:
                                continue
            return

        if provider == "mistral":
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.mistral_api_key}",
            }
            mi_stream_msgs = []
            if system_prompt:
                mi_stream_msgs.append({"role": "system", "content": system_prompt})
            mi_stream_msgs.append({"role": "user", "content": prepared_prompt})
            data = {
                "model": model,
                "messages": mi_stream_msgs,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
            }
            with requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=120,
                stream=True,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode("utf-8")
                        if line_str.startswith("data: ") and line_str != "data: [DONE]":
                            import json as _json
                            try:
                                chunk_data = _json.loads(line_str[6:])
                                content = chunk_data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content:
                                    yield content
                            except _json.JSONDecodeError:
                                continue
            return

        raise ValueError(f"Unsupported LLM provider for streaming: {provider}")
