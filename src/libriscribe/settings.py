# src/libriscribe/settings.py
from libriscribe.utils.paths import (
    get_default_projects_dir,
    get_default_env_path,
    get_writing_prompt_path,
)

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""  # Optional, can be empty
    openai_model: str = "gpt-4o-mini"
    google_ai_studio_api_key: str = ""
    google_ai_studio_model: str = "gemini-2.5-flash"
    claude_api_key: str = ""
    claude_model: str = "claude-3-opus-20240229"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-coder-6.7b-instruct"
    mistral_api_key: str = ""
    mistral_model: str = "mistral-medium-latest"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "anthropic/claude-3-haiku"
    # Local / OpenAI-compatible (LM Studio, Ollama, llama.cpp, vLLM). Requests go
    # only to this base URL, so nothing leaves the machine.
    local_api_key: str = ""
    local_base_url: str = "http://localhost:1234/v1"
    local_model: str = ""
    fallback_chain: str = ""
    projects_dir: str = str(get_default_projects_dir())
    default_llm: str = "openai"  # Set a default

    # Retrieval Defaults
    retrieval_enabled: bool = False
    retrieval_default_mode: str = "disabled"
    retrieval_backend: str = "local"
    retrieval_embedding_provider: str = "sentence-transformers"
    retrieval_embedding_model: str = "all-MiniLM-L6-v2"
    retrieval_chroma_path: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    mongodb_vector_uri: str = ""
    pinecone_api_key: str = ""
    pinecone_index_name: str = ""
    weaviate_url: str = ""
    weaviate_api_key: str = ""

    writing_system_prompt: str = ""

    model_config = SettingsConfigDict(
        env_file=str(get_default_env_path()),
        extra="ignore",
    )  # type: ignore

    @model_validator(mode="after")
    def _load_writing_prompt_from_file(self):
        """The writing system prompt lives in its own (multi-line) file. Load it
        when not provided via env, so consumers reading settings.writing_system_prompt
        get the saved value."""
        if not self.writing_system_prompt:
            try:
                path = get_writing_prompt_path()
                if path.exists():
                    text = path.read_text(encoding="utf-8")
                    if text.strip():
                        self.writing_system_prompt = text
            except Exception:
                pass
        return self

