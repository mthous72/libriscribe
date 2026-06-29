"""Settings endpoints - read/write API keys via .env."""
from __future__ import annotations

from fastapi import APIRouter
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
    default_llm: str = "openai"
    retrieval_enabled: bool = False


class ProviderStatus(BaseModel):
    name: str
    configured: bool = False
    model: str = ""


def _mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return "***" if key else ""
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
        default_llm=s.default_llm,
        retrieval_enabled=s.retrieval_enabled,
    )


@router.get("/providers", response_model=list[ProviderStatus])
def get_providers():
    from libriscribe.settings import Settings
    s = Settings()
    return [
        ProviderStatus(name="openai", configured=bool(s.openai_api_key), model=s.openai_model),
        ProviderStatus(name="claude", configured=bool(s.claude_api_key), model=s.claude_model),
        ProviderStatus(name="google_ai_studio", configured=bool(s.google_ai_studio_api_key), model=s.google_ai_studio_model),
        ProviderStatus(name="deepseek", configured=bool(s.deepseek_api_key), model=s.deepseek_model),
        ProviderStatus(name="mistral", configured=bool(s.mistral_api_key), model=s.mistral_model),
        ProviderStatus(name="openrouter", configured=bool(s.openrouter_api_key), model=s.openrouter_model),
    ]
