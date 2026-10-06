"""
config.py — Central configuration for TruthGuard AI.

WHAT THIS DOES (beginner explanation):
    Instead of hard-coding secret API keys in the code (never do this!), we read
    them from environment variables. `pydantic-settings` automatically loads a
    local `.env` file (if present) plus any real environment variables, validates
    the types, and gives us one tidy `Settings` object used across the app.

    Copy `.env.example` -> `.env` and fill in your keys. The `.env` file must be
    in the same folder where you start uvicorn (the project root).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---------------------------------------------------------------
    # Hugging Face — used by Part 1 (deepfake image detection)
    # ---------------------------------------------------------------
    # Your personal access token from https://huggingface.co/settings/tokens
    # A token with "Read" permission is enough.
    hf_token: str = ""

    # The pre-trained model on the HF Hub. This one is a Vision Transformer
    # fine-tuned for binary "fake vs real" image classification (~86M params).
    # You can swap it for any other fake-vs-real image-classification model.
    deepfake_model_id: str = "dima806/deepfake_vs_real_image_detection"

    # Since late 2025 the old "Serverless Inference API" is called
    # "Inference Providers". "hf-inference" is Hugging Face's own provider and
    # still serves CPU-friendly tasks like image classification.
    hf_provider: str = "hf-inference"

    # How long (seconds) to wait for Hugging Face before giving up.
    hf_timeout_seconds: int = 60

    # ---------------------------------------------------------------
    # Groq — used by Part 2 (fact-checking LLM)
    # ---------------------------------------------------------------
    # API key from https://console.groq.com/keys (free tier).
    groq_api_key: str = ""

    # IMPORTANT (Oct 2026): Groq retired "llama-3.1-8b-instant" on 2026-08-16
    # for free/developer accounts. Their official replacement is
    # "openai/gpt-oss-20b" — fast, free-tier friendly, supports JSON mode.
    groq_model: str = "openai/gpt-oss-20b"

    # 0.0 = most deterministic answers (best for fact-checking).
    groq_temperature: float = 0.0

    # Max tokens the LLM may generate (includes hidden reasoning tokens for
    # gpt-oss models, so don't set this too low).
    groq_max_tokens: int = 2048

    groq_timeout_seconds: int = 30

    # ---------------------------------------------------------------
    # Web search — used by Part 2 to ground the fact-check in real sources
    # ---------------------------------------------------------------
    # OPTIONAL. Free key from https://app.tavily.com (1,000 credits/month).
    # If left empty, the app falls back to keyless DuckDuckGo search (ddgs),
    # which works but can be rate-limited from some networks.
    tavily_api_key: str = ""

    # How many search results to feed to the LLM as context (2-3 is plenty).
    search_max_results: int = 3

    search_timeout_seconds: int = 10

    # ---------------------------------------------------------------
    # App behaviour
    # ---------------------------------------------------------------
    # Reject uploads bigger than this (protects you and the HF free tier).
    max_image_mb: int = 8

    # Comma-separated list of frontend origins allowed to call this API.
    # Your React teammate's dev server will run on one of these.
    cors_origins: str = (
        "http://localhost:3000,"   # React (create-react-app)
        "http://localhost:5173,"   # Vite / React
        "http://localhost:4200,"   # Angular
        "http://127.0.0.1:3000,"
        "http://127.0.0.1:5173"
    )

    # Tell pydantic-settings to read a `.env` file next to main.py and to
    # ignore unknown variables (so extra vars in .env don't crash startup).
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------------------------------------------------------------
    # Helper properties
    # ---------------------------------------------------------------
    @property
    def cors_origins_list(self) -> list[str]:
        """Split the comma-separated CORS_ORIGINS string into a real list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def search_provider(self) -> str:
        """Which search backend will be used, given the current config."""
        return "tavily" if self.tavily_api_key else "duckduckgo"


@lru_cache
def get_settings() -> Settings:
    """
    Returns a single shared Settings instance (cached).
    Use `get_settings()` anywhere in the app instead of creating Settings()
    again — it guarantees everyone reads the same .env values.
    """
    return Settings()
