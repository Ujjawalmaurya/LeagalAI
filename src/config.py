from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Reload .env if it changes
load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CHROMA_DIR = BASE_DIR / "data" / "chroma_db"


@dataclass(frozen=True)
class AppConfig:
    gemini_api_key: str
    chat_model: str = "gemini-3.6-flash"
    embedding_model: str = "gemini-embedding-001"
    chroma_dir: Path = DEFAULT_CHROMA_DIR
    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k_retrieval: int = 5


def get_config(
    api_key_override: str | None = None,
    embedding_model_override: str | None = None,
    chat_model_override: str | None = None,
    **kwargs,
) -> AppConfig:
    load_dotenv(override=True)
    key = api_key_override or os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    return AppConfig(
        gemini_api_key=key.strip(),
        embedding_model=embedding_model_override or "gemini-embedding-001",
        chat_model=chat_model_override or "gemini-3.6-flash",
    )
