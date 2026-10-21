from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# api/app/config.py -> api/ -> repo root
_API_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _API_DIR.parent


class Settings(BaseSettings):
    # Absolute paths, not a bare ".env": the server is normally started from
    # api/ while the env file lives at the repo root, and a relative path would
    # silently resolve against the working directory and load nothing.
    # Later entries win, so api/.env can override the shared root file.
    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", _API_DIR / ".env"),
        extra="ignore",
    )

    # --- LLM ---
    llm_provider: Literal["gemini", "groq", "anthropic", "openai"] = "gemini"
    llm_fallback_provider: Literal[
        "groq", "gemini", "anthropic", "openai", "none"
    ] = "groq"

    gemini_api_key: str = ""
    # Pinned rather than using the "gemini-flash-latest" alias so a silent
    # upstream model swap can't change answer quality without a commit.
    # Google retires older ids for new keys, so re-check this when onboarding:
    #   uv run python -c "from google import genai; from app.config import settings; \
    #   [print(m.name) for m in genai.Client(api_key=settings.gemini_api_key).models.list()]"
    gemini_model: str = "gemini-3.6-flash"

    groq_api_key: str = ""
    # llama-3.3-70b-versatile was retired from Groq's catalog (the API answers 404
    # model_not_found), which silently turned the failover into a no-op. Check
    # what the key can use with: GET https://api.groq.com/openai/v1/models
    groq_model: str = "openai/gpt-oss-120b"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5"

    openai_api_key: str = ""
    openai_model: str = "gpt-6-luna"

    # --- Retrieval ---
    # MiniLM (384-dim, 0.22GB) keeps CPU embedding fast enough for a 2-vCPU host.
    # Set to "intfloat/multilingual-e5-large" + dense_dim=1024 for better recall
    # at roughly 10x the model size and much slower CPU inference.
    dense_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    dense_dim: int = 384
    sparse_model: str = "Qdrant/bm25"
    rerank_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"

    top_k_dense: int = 50
    top_k_sparse: int = 50
    fusion_limit: int = 30
    rerank_to: int = 8

    # --- Chunking ---
    chunk_target_tokens: int = 800
    chunk_overlap_tokens: int = 100

    # --- Storage ---
    qdrant_path: str = "./data/qdrant"
    qdrant_url: str = ""  # set this to use a remote Qdrant instead of embedded
    collection: str = "kb_chunks"
    workspace_ttl_hours: int = 24

    # --- Upload caps ---
    max_file_mb: int = 5
    max_files_per_workspace: int = 3
    max_pages_per_doc: int = 100
    parse_timeout_seconds: int = 30

    # --- OCR (release 2) ---
    ocr_enabled: bool = False
    ocr_max_pages_per_workspace: int = 30
    ocr_dpi: int = 150
    ocr_batch_pages: int = 5

    # --- Page router thresholds ---
    router_min_chars: int = 200
    router_min_image_coverage: float = 0.7
    router_min_space_ratio: float = 0.05

    # --- Demo guardrails ---
    demo_enabled: bool = True
    session_secret: str = "dev-only-change-me"
    rate_limit_chat: str = "10/minute"
    rate_limit_upload: str = "5/hour"
    daily_llm_call_budget: int = 500
    cors_origins: str = "http://localhost:3000"

    @property
    def max_file_bytes(self) -> int:
        return self.max_file_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
