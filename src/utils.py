from __future__ import annotations

import ast
from typing import Any


def extract_text_from_response(value: Any) -> str:
    # Gemini can return a list of text blocks instead of a string. Convert to normal text.
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
    # Split items into two lists for side by side display
    left = items[::2]
    right = items[1::2]
    return left, right


def render_citations(citations: list[dict], streamlit_module: Any) -> None:
    # Show referenced lines in an expander
    st = streamlit_module
    if not citations:
        return

    with st.expander(f"Referenced sections ({len(citations)})"):
        for cite in citations:
            ref = cite.get("ref", 1)
            page = cite.get("page", 1)
            source = cite.get("source", "Document")
            text = cite.get("full_text", "").strip()

            st.markdown(f"**Section {ref}** (Page {page}, `{source}`)")
            st.markdown(f"> {text}")
            st.write("")
