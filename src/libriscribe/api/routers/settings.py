"""Settings endpoints - read/write API keys via .env, list provider models."""
from __future__ import annotations

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from libriscribe.utils.paths import get_default_env_path

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    openai_api_key: str = ""
    openai_model: str = ""
    google_ai_studio_api_key: str = ""
    google_ai_studio_model: str = ""
    claude_api_key: str = ""
    claude_model: str = ""
    deepseek_api_key: str = ""
    deepseek_model: str = ""
    mistral_api_key: str = ""
    mistral_model: str = ""
    openrouter_api_key: str = ""
    openrouter_model: str = ""
    local_api_key: str = ""
    local_base_url: str = ""
    local_model: str = ""
    default_llm: str = "openai"
    retrieval_enabled: bool = False


class ProviderStatus(BaseModel):
    name: str
    configured: bool = False
    model: str = ""


# Placeholder values that should be treated as "no key set" (e.g. seeded from an
# older .env.example). Compared case-insensitively after stripping.
_PLACEHOLDER_KEYS = {"", "your_api_key_here", "your-api-key-here", "changeme"}


def _is_real_key(key: str) -> bool:
    return bool(key) and key.strip().lower() not in _PLACEHOLDER_KEYS


def _mask_key(key: str) -> str:
    if not _is_real_key(key):
        return ""
    if len(key) < 8:
        return "***"
    return key[:4] + "..." + key[-4:]


@router.get("", response_model=SettingsResponse)
def get_settings():
    from libriscribe.settings import Settings
    s = Settings()
    return SettingsResponse(
        openai_api_key=_mask_key(s.openai_api_key),
        openai_model=s.openai_model,
        google_ai_studio_api_key=_mask_key(s.google_ai_studio_api_key),
        google_ai_studio_model=s.google_ai_studio_model,
        claude_api_key=_mask_key(s.claude_api_key),
        claude_model=s.claude_model,
        deepseek_api_key=_mask_key(s.deepseek_api_key),
        deepseek_model=s.deepseek_model,
        mistral_api_key=_mask_key(s.mistral_api_key),
        mistral_model=s.mistral_model,
        openrouter_api_key=_mask_key(s.openrouter_api_key),
        openrouter_model=s.openrouter_model,
        local_api_key=_mask_key(s.local_api_key),
        local_base_url=s.local_base_url,
        local_model=s.local_model,
        default_llm=s.default_llm,
        retrieval_enabled=s.retrieval_enabled,
    )


@router.put("", response_model=SettingsResponse)
def update_settings(body: dict):
    """Updates .env file with new settings values."""
    env_path = get_default_env_path()
    existing = {}

    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                existing[key.strip()] = value.strip()

    # Map settings fields to .env keys
    field_to_env = {
        "openai_api_key": "OPENAI_API_KEY",
        "openai_model": "OPENAI_MODEL",
        "google_ai_studio_api_key": "GOOGLE_AI_STUDIO_API_KEY",
        "google_ai_studio_model": "GOOGLE_AI_STUDIO_MODEL",
        "claude_api_key": "CLAUDE_API_KEY",
        "claude_model": "CLAUDE_MODEL",
        "deepseek_api_key": "DEEPSEEK_API_KEY",
        "deepseek_model": "DEEPSEEK_MODEL",
        "mistral_api_key": "MISTRAL_API_KEY",
        "mistral_model": "MISTRAL_MODEL",
        "openrouter_api_key": "OPENROUTER_API_KEY",
        "openrouter_model": "OPENROUTER_MODEL",
        "local_api_key": "LOCAL_API_KEY",
        "local_base_url": "LOCAL_BASE_URL",
        "local_model": "LOCAL_MODEL",
        "default_llm": "DEFAULT_LLM",
        "retrieval_enabled": "RETRIEVAL_ENABLED",
    }

    for field, env_key in field_to_env.items():
        if field in body:
            value = body[field]
            # Don't overwrite keys with masked values
            if isinstance(value, str) and "..." in value:
                continue
            existing[env_key] = str(value)

    # Write back
    env_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{k}={v}" for k, v in existing.items()]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Clear cached settings
    from libriscribe.api.dependencies import get_settings
    get_settings.cache_clear()

    return get_settings_response()


def get_settings_response():
    from libriscribe.settings import Settings
    s = Settings()
    return SettingsResponse(
        openai_api_key=_mask_key(s.openai_api_key),
        openai_model=s.openai_model,
        google_ai_studio_api_key=_mask_key(s.google_ai_studio_api_key),
        google_ai_studio_model=s.google_ai_studio_model,
        claude_api_key=_mask_key(s.claude_api_key),
        claude_model=s.claude_model,
        deepseek_api_key=_mask_key(s.deepseek_api_key),
        deepseek_model=s.deepseek_model,
        mistral_api_key=_mask_key(s.mistral_api_key),
        mistral_model=s.mistral_model,
        openrouter_api_key=_mask_key(s.openrouter_api_key),
        openrouter_model=s.openrouter_model,
        local_api_key=_mask_key(s.local_api_key),
        local_base_url=s.local_base_url,
        local_model=s.local_model,
        default_llm=s.default_llm,
        retrieval_enabled=s.retrieval_enabled,
    )


# ─── Model listing (B6) ──────────────────────────────────────────────────────

class ModelListRequest(BaseModel):
    provider: str
    api_key: str | None = None
    base_url: str | None = None


class ModelInfo(BaseModel):
    id: str
    label: str
    free: bool = False


_PROVIDER_SAVED_KEY = {
    "openai": "openai_api_key",
    "claude": "claude_api_key",
    "google_ai_studio": "google_ai_studio_api_key",
    "deepseek": "deepseek_api_key",
    "mistral": "mistral_api_key",
    "openrouter": "openrouter_api_key",
    "local": "local_api_key",
}


def _openai_compatible_models(base_url: str, key: str) -> list[ModelInfo]:
    resp = requests.get(
        f"{base_url.rstrip('/')}/models",
        headers={"Authorization": f"Bearer {key}"},
        timeout=10,
    )
    resp.raise_for_status()
    out = []
    for m in resp.json().get("data", []):
        mid = m.get("id")
        if mid:
            out.append(ModelInfo(id=mid, label=mid))
    return out


def _openrouter_models(base_url: str, key: str | None) -> list[ModelInfo]:
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    resp = requests.get(f"{base_url.rstrip('/')}/models", headers=headers, timeout=10)
    resp.raise_for_status()
    out = []
    for m in resp.json().get("data", []):
        mid = m.get("id")
        if not mid:
            continue
        pricing = m.get("pricing") or {}
        free = str(pricing.get("prompt")) == "0" and str(pricing.get("completion")) == "0"
        out.append(ModelInfo(id=mid, label=m.get("name") or mid, free=free))
    return out


def _anthropic_models(key: str) -> list[ModelInfo]:
    resp = requests.get(
        "https://api.anthropic.com/v1/models",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
        timeout=10,
    )
    resp.raise_for_status()
    out = []
    for m in resp.json().get("data", []):
        mid = m.get("id")
        if mid:
            out.append(ModelInfo(id=mid, label=m.get("display_name") or mid))
    return out


def _gemini_models(key: str) -> list[ModelInfo]:
    resp = requests.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        params={"key": key},
        timeout=10,
    )
    resp.raise_for_status()
    out = []
    for m in resp.json().get("models", []):
        if "generateContent" not in (m.get("supportedGenerationMethods") or []):
            continue
        name = m.get("name", "")
        mid = name.split("/", 1)[1] if name.startswith("models/") else name
        if mid:
            out.append(ModelInfo(id=mid, label=m.get("displayName") or mid))
    return out


@router.post("/models", response_model=list[ModelInfo])
def list_provider_models(body: ModelListRequest):
    """Fetch the available models for a provider using the supplied or saved key."""
    provider = body.provider
    if provider not in _PROVIDER_SAVED_KEY:
        raise HTTPException(status_code=400, detail="unsupported_provider")

    # Prefer a freshly-entered key; fall back to the saved one. Masked values
    # (containing "...") are not real keys and fall through to the saved key.
    key = body.api_key if _is_real_key(body.api_key or "") else None
    if not key:
        from libriscribe.settings import Settings

        saved = getattr(Settings(), _PROVIDER_SAVED_KEY[provider], "")
        key = saved if _is_real_key(saved) else None

    # OpenRouter and local servers can list without a key; others need one.
    if not key and provider not in ("openrouter", "local"):
        raise HTTPException(status_code=400, detail="missing_key — enter or save an API key first")

    try:
        if provider == "openai":
            models = _openai_compatible_models("https://api.openai.com/v1", key)
        elif provider == "deepseek":
            models = _openai_compatible_models("https://api.deepseek.com", key)
        elif provider == "mistral":
            models = _openai_compatible_models("https://api.mistral.ai/v1", key)
        elif provider == "openrouter":
            models = _openrouter_models(body.base_url or "https://openrouter.ai/api/v1", key)
        elif provider == "local":
            from libriscribe.settings import Settings as _LocalSettings

            base = body.base_url or _LocalSettings().local_base_url or "http://localhost:1234/v1"
            models = _openai_compatible_models(base, key or "not-needed")
        elif provider == "claude":
            models = _anthropic_models(key)
        else:  # google_ai_studio
            models = _gemini_models(key)
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else 502
        if code in (401, 403):
            raise HTTPException(status_code=400, detail="invalid_key — the API key was rejected")
        raise HTTPException(status_code=502, detail=f"provider_error ({code})")
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="network_error — could not reach the provider")

    # Free models first, then alphabetical.
    models.sort(key=lambda m: (not m.free, m.id.lower()))
    return models


@router.get("/providers", response_model=list[ProviderStatus])
def get_providers():
    from libriscribe.settings import Settings
    s = Settings()
    return [
        ProviderStatus(name="openai", configured=_is_real_key(s.openai_api_key), model=s.openai_model),
        ProviderStatus(name="claude", configured=_is_real_key(s.claude_api_key), model=s.claude_model),
        ProviderStatus(name="google_ai_studio", configured=_is_real_key(s.google_ai_studio_api_key), model=s.google_ai_studio_model),
        ProviderStatus(name="deepseek", configured=_is_real_key(s.deepseek_api_key), model=s.deepseek_model),
        ProviderStatus(name="mistral", configured=_is_real_key(s.mistral_api_key), model=s.mistral_model),
        ProviderStatus(name="openrouter", configured=_is_real_key(s.openrouter_api_key), model=s.openrouter_model),
        ProviderStatus(name="local", configured=bool(s.local_base_url), model=s.local_model),
    ]
