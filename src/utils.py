from __future__ import annotations

import ast
from typing import Any


def extract_text_from_response(value: Any) -> str:
    """
    Gemini sometimes returns content as a JSON-encoded list of text blocks
    instead of a plain string. This unwraps that and returns clean text.
    """
    if not isinstance(value, str):
        return str(value) if value is not None else ""

    looks_like_block_list = value.startswith("[{'type': 'text'") or value.startswith('[{"type": "text"')
    if not looks_like_block_list:
        return value

    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, list):
            text_parts = [block.get("text", "") for block in parsed if isinstance(block, dict)]
            return "\n".join(text_parts).strip()
    except Exception:
        pass

    return value


def split_into_two_columns(items: list) -> tuple[list, list]:
    """
    Splits a flat list into two roughly equal halves for side-by-side display.
    Even-indexed items go left, odd-indexed go right.
    """
    left = items[::2]
    right = items[1::2]
    return left, right


def render_citations(citations: list[dict], streamlit_module: Any) -> None:
    """
    Renders a list of clause citations as an expander with formatted markdown.
    Extracted here so the same rendering logic isn't duplicated across
    chat history and the live response block.
    """
    st = streamlit_module
    if not citations:
        return

    with st.expander(f"Referenced clauses ({len(citations)})"):
        for cite in citations:
            ref = cite.get("ref", 1)
            page = cite.get("page", 1)
            source = cite.get("source", "Document")
            text = cite.get("full_text", "").strip()

            st.markdown(f"**Clause {ref}** (Page {page}, `{source}`)")
            st.markdown(f"> {text}")
            st.write("")
