from __future__ import annotations

import shutil
from pathlib import Path
from typing import Sequence

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.config import AppConfig, get_config


def get_embeddings(config: AppConfig) -> GoogleGenerativeAIEmbeddings:
    # Fail fast if key is missing instead of throwing generic errors deep in Chroma
    if not config.gemini_api_key:
        raise ValueError(
            "Google API key is missing. Set GOOGLE_API_KEY in .env or provide it in the sidebar."
        )

    return GoogleGenerativeAIEmbeddings(
        model=config.embedding_model,
        google_api_key=config.gemini_api_key,
    )


def get_vectorstore(
    config: AppConfig | None = None,
    collection_name: str = "legal_documents",
) -> Chroma:
    cfg = config or get_config()
    embeddings = get_embeddings(cfg)
    persist_dir = str(cfg.chroma_dir)

    Path(persist_dir).mkdir(parents=True, exist_ok=True)

    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )


def index_documents(
    documents: Sequence[Document],
    config: AppConfig | None = None,
    collection_name: str = "legal_documents",
) -> int:
    if not documents:
        return 0

    vectorstore = get_vectorstore(config=config, collection_name=collection_name)
    vectorstore.add_documents(documents=list(documents))
    return len(documents)


def retrieve_relevant_clauses(
    query: str,
    config: AppConfig | None = None,
    k: int = 5,
    collection_name: str = "legal_documents",
) -> list[Document]:
    # MMR prevents fetching 5 copies of the same boilerplate clause
    vectorstore = get_vectorstore(config=config, collection_name=collection_name)
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        # fetch_k is the candidate pool MMR picks from — larger pool = more diverse results
        search_kwargs={"k": k, "fetch_k": max(k * 4, 20)},
    )
    return retriever.invoke(query)


def clear_vectorstore(
    config: AppConfig | None = None,
    collection_name: str = "legal_documents",
) -> None:
    cfg = config or get_config()
    try:
        store = get_vectorstore(config=cfg, collection_name=collection_name)
        store.delete_collection()
    except Exception:
        # If Chroma's handle is locked or stale, nuke the folder directly
        if cfg.chroma_dir.exists():
            shutil.rmtree(cfg.chroma_dir, ignore_errors=True)
