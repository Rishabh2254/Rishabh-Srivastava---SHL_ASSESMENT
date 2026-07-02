"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    llm_model: str = Field(default="", alias="LLM_MODEL")

    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL"
    )
    catalog_path: Path = Field(
        default=PROJECT_ROOT / "catalog" / "data" / "shl_catalog.json",
        alias="CATALOG_PATH",
    )
    vectorstore_path: Path = Field(
        default=PROJECT_ROOT / "vectorstore" / "faiss.index",
        alias="VECTORSTORE_PATH",
    )
    vectorstore_meta_path: Path = Field(
        default=PROJECT_ROOT / "vectorstore" / "metadata.json",
        alias="VECTORSTORE_META_PATH",
    )

    retrieval_top_k: int = Field(default=20, alias="RETRIEVAL_TOP_K")
    rerank_top_k: int = Field(default=10, alias="RERANK_TOP_K")
    min_retrieval_score: float = Field(default=0.25, alias="MIN_RETRIEVAL_SCORE")
    max_conversation_turns: int = Field(default=8, alias="MAX_CONVERSATION_TURNS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT


@lru_cache
def get_settings() -> Settings:
    return Settings()
