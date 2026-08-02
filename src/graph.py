from __future__ import annotations

from typing import Any, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph

from src.config import AppConfig, get_config
from src.prompts import LEGAL_ANALYSIS_SYSTEM_PROMPT, LEGAL_QA_USER_TEMPLATE
from src.vectorstore import retrieve_relevant_clauses


class LegalQAState(TypedDict):
    question: str
    documents: list[Document]
    context_text: str
    citations: list[dict[str, Any]]
    answer: str


def create_retrieve_node(config: AppConfig):
    def retrieve_node(state: LegalQAState) -> dict[str, Any]:
        query = state.get("question", "").strip()
        if not query:
            return {"documents": [], "context_text": "", "citations": []}

        docs = retrieve_relevant_clauses(
            query=query,
            config=config,
            k=config.top_k_retrieval,
        )

        context_parts: list[str] = []
        citations: list[dict[str, Any]] = []

        for idx, doc in enumerate(docs, start=1):
            source = doc.metadata.get("source", "Document")
            page = doc.metadata.get("page", 1)
            chunk_idx = doc.metadata.get("chunk_index", idx)
            content = doc.page_content.strip()

            tag = f"[Clause Ref #{idx} | {source} - Page {page}]"
            context_parts.append(f"{tag}\n{content}")

            citations.append(
                {
                    "ref": idx,
                    "source": source,
                    "page": page,
                    "chunk_index": chunk_idx,
                    "snippet": content[:240] + ("..." if len(content) > 240 else ""),
                    "full_text": content,
                }
            )

        return {
            "documents": docs,
            "context_text": "\n\n---\n\n".join(context_parts),
            "citations": citations,
        }

    return retrieve_node


def _extract_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
            elif hasattr(block, "text"):
                parts.append(str(block.text))
        return "\n".join(parts).strip()
    return str(content).strip()


def create_generate_node(config: AppConfig):
    def generate_node(state: LegalQAState) -> dict[str, Any]:
        context_text = state.get("context_text", "").strip()
        question = state.get("question", "").strip()

        if not context_text:
            return {
                "answer": (
                    "No relevant clauses found in this document. "
                    "Make sure the file uploaded properly, or try searching with different words."
                )
            }

        llm = ChatGoogleGenerativeAI(
            model=config.chat_model,
            google_api_key=config.gemini_api_key,
            temperature=0.2,
        )

        user_content = LEGAL_QA_USER_TEMPLATE.format(
            context=context_text,
            question=question,
        )

        messages = [
            SystemMessage(content=LEGAL_ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]

        response = llm.invoke(messages)
        return {"answer": _extract_text(response.content)}

    return generate_node


def build_legal_qa_graph(config: AppConfig | None = None):
    cfg = config or get_config()

    workflow = StateGraph(LegalQAState)
    workflow.add_node("retrieve", create_retrieve_node(cfg))
    workflow.add_node("generate", create_generate_node(cfg))

    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


def run_legal_analysis(
    question: str,
    config: AppConfig | None = None,
) -> dict[str, Any]:
    cfg = config or get_config()
    graph = build_legal_qa_graph(cfg)

    initial_state: LegalQAState = {
        "question": question,
        "documents": [],
        "context_text": "",
        "citations": [],
        "answer": "",
    }

    return graph.invoke(initial_state)


_SUGGESTION_PROMPT = """You are looking at chunks from a legal document.

Based only on what's actually in these chunks, write 6 short questions that someone would genuinely want to ask before agreeing to this document.

Rules:
- Make each question specific to this document, not generic.
- Keep each question under 12 words.
- No duplicates, no fluff.
- Return ONLY a JSON array of 6 strings. No explanation, no markdown, just the array.

Example output:
["Can they share my data with advertisers?", "What happens if I miss a payment?", ...]"""


def generate_suggested_questions(config: AppConfig | None = None) -> list[str]:
    """Do a broad retrieval then ask the LLM to generate document-specific questions."""
    cfg = config or get_config()

    # Broad seed so MMR samples diverse chunks from across the document
    docs = retrieve_relevant_clauses(
        query=(
            "overview rights obligations data privacy payment cancellation "
            "arbitration liability termination third party disclosure auto-renewal"
        ),
        config=cfg,
        k=10,
    )

    if not docs:
        return []

    context = "\n\n---\n\n".join(d.page_content.strip() for d in docs)

    llm = ChatGoogleGenerativeAI(
        model=cfg.chat_model,
        google_api_key=cfg.gemini_api_key,
        temperature=0.3,
    )

    messages = [
        SystemMessage(content=_SUGGESTION_PROMPT),
        HumanMessage(content=f"Document chunks:\n\n{context}"),
    ]

    try:
        response = llm.invoke(messages)
        raw = _extract_text(response.content).strip()
        # Strip markdown code fences if the model wraps it
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        import json
        questions = json.loads(raw.strip())
        if isinstance(questions, list):
            return [str(q) for q in questions[:6]]
    except Exception:
        pass

    return []
