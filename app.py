from __future__ import annotations
# Inspired by tosdr.org (simplifies terms and conditions).

import os
import streamlit as st
from dotenv import load_dotenv

from src.config import AppConfig
from src.document_loader import extract_documents_from_upload, split_legal_documents
from src.graph import generate_suggested_questions, run_legal_analysis
from src.utils import extract_text_from_response, render_citations, split_into_two_columns
from src.vectorstore import clear_vectorstore, index_documents

load_dotenv(override=True)

st.set_page_config(
    page_title="Legal AI",
    layout="wide",
    initial_sidebar_state="auto",
)

# Session state setup
if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_doc_name" not in st.session_state:
    st.session_state.active_doc_name = None
if "indexed_chunks_count" not in st.session_state:
    st.session_state.indexed_chunks_count = 0
if "prompt_to_submit" not in st.session_state:
    st.session_state.prompt_to_submit = None
if "suggested_questions" not in st.session_state:
    st.session_state.suggested_questions = []
if "index_stats" not in st.session_state:
    # Save part settings to display in sidebar
    st.session_state.index_stats = {}

api_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()


# ---------------------------------------------------------------------------
# Sidebar - document upload and details
# ---------------------------------------------------------------------------
with st.sidebar:
    st.subheader("Document")
    uploaded_file = st.file_uploader(
        "Upload document",
        type=["pdf", "docx", "txt", "md"],
        label_visibility="collapsed",
    )

    if not api_key:
        st.warning("GOOGLE_API_KEY is missing in your .env file.")

    # Read and save the uploaded file
    if uploaded_file is not None:
        file_name = uploaded_file.name
        is_new_file = st.session_state.active_doc_name != file_name

        if is_new_file:
            if st.button("Scan document", type="primary", use_container_width=True):
                if not api_key:
                    st.error("Cannot scan: GOOGLE_API_KEY is missing in your .env file.")
                else:
                    with st.status("Reading document...", expanded=True) as status:
                        try:
                            cfg = AppConfig(gemini_api_key=api_key)
                            clear_vectorstore(cfg)

                            file_bytes = uploaded_file.read()
                            raw_docs = extract_documents_from_upload(file_bytes, file_name)

                            if not raw_docs:
                                status.update(label="Could not find any text in this file.", state="error")
                            else:
                                chunks = split_legal_documents(
                                    raw_docs,
                                    chunk_size=cfg.chunk_size,
                                    chunk_overlap=cfg.chunk_overlap,
                                )
                                count = index_documents(chunks, config=cfg)

                                st.session_state.active_doc_name = file_name
                                st.session_state.indexed_chunks_count = count
                                st.session_state.messages = []
                                st.session_state.index_stats = {
                                    "chunks": count,
                                    "chunk_size": cfg.chunk_size,
                                    "chunk_overlap": cfg.chunk_overlap,
                                    "top_k": cfg.top_k_retrieval,
                                    "chat_model": cfg.chat_model,
                                    "embedding_model": cfg.embedding_model,
                                    "storage": str(cfg.chroma_dir.relative_to(cfg.chroma_dir.parent.parent)),
                                }

                                status.update(label="Finding sample questions...", state="running")
                                st.session_state.suggested_questions = generate_suggested_questions(cfg)

                                status.update(
                                    label=f"Ready: {file_name} ({count} sections)",
                                    state="complete",
                                    expanded=False,
                                )
                                st.rerun()
                        except Exception as err:
                            status.update(label=f"Could not load file: {err}", state="error")

    if st.session_state.active_doc_name:
        st.write("---")
        st.caption(f"Active: **{st.session_state.active_doc_name}** ({st.session_state.indexed_chunks_count} sections)")
        if st.button("Remove document", use_container_width=True):
            cfg = AppConfig(gemini_api_key=api_key)
            clear_vectorstore(cfg)
            st.session_state.active_doc_name = None
            st.session_state.indexed_chunks_count = 0
            st.session_state.messages = []
            st.session_state.suggested_questions = []
            st.session_state.index_stats = {}
            st.rerun()

    # Details panel - shown after document is ready
    if st.session_state.index_stats:
        stats = st.session_state.index_stats
        st.write("---")
        st.caption("**Document details**")
        st.caption(f"Sections saved: `{stats['chunks']}`")
        st.caption(f"Section size: `{stats['chunk_size']}` chars")
        st.caption(f"Overlap: `{stats['chunk_overlap']}` chars")
        st.caption(f"Search count: `{stats['top_k']}`")
        st.write("")
        st.caption("**Models**")
        st.caption(f"Chat: `{stats['chat_model']}`")
        st.caption(f"Embedding: `{stats['embedding_model']}`")
        st.write("")
        st.caption("**Storage**")
        st.caption(f"`{stats['storage']}`")


current_config = AppConfig(gemini_api_key=api_key)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FALLBACK_QUESTIONS = [
    "🔍 Quick summary — what should I know first?",
    "🚩 What parts are unfair or risky for me?",
    "💸 Can they change prices without telling me?",
    "🔒 What personal data do they collect and share?",
    "❌ How can I cancel, and will it auto-renew?",
    "⚖️ What happens if something goes wrong?",
]


def render_question_grid(questions: list[str], key_prefix: str) -> None:
    # Show questions in two columns side by side
    left_questions, right_questions = split_into_two_columns(questions)
    left_col, right_col = st.columns(2)

    with left_col:
        for index, question in enumerate(left_questions):
            if st.button(question, key=f"{key_prefix}_left_{index}", use_container_width=True):
                st.session_state.prompt_to_submit = question
                st.rerun()

    with right_col:
        for index, question in enumerate(right_questions):
            if st.button(question, key=f"{key_prefix}_right_{index}", use_container_width=True):
                st.session_state.prompt_to_submit = question
                st.rerun()


# ---------------------------------------------------------------------------
# Main screen
# ---------------------------------------------------------------------------
st.title("Legal AI")
st.caption("Find risky terms and unfair rules in simple words.")

# Show suggestions before user starts chatting
if st.session_state.active_doc_name and not st.session_state.messages:
    questions = st.session_state.suggested_questions or FALLBACK_QUESTIONS
    heading = "Questions you can ask:" if st.session_state.suggested_questions else "Try asking one of these:"

    _padding, centre, _padding = st.columns([1, 3, 1])
    with centre:
        st.write(heading)
        render_question_grid(questions, key_prefix="suggest")

elif not st.session_state.active_doc_name:
    st.info("Upload a PDF, DOCX, or TXT document in the sidebar to start.")


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(extract_text_from_response(msg["content"]))
        render_citations(msg.get("citations", []), st)


# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
user_input = st.chat_input("Ask anything about this document...")

if st.session_state.prompt_to_submit:
    user_input = st.session_state.prompt_to_submit
    st.session_state.prompt_to_submit = None

if user_input:
    if not current_config.gemini_api_key:
        st.error("Please add GOOGLE_API_KEY in your .env file.")
    elif not st.session_state.active_doc_name:
        st.warning("Please upload a document first.")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Reading document and finding answer..."):
                try:
                    result = run_legal_analysis(user_input, config=current_config)
                    answer = result.get("answer", "Could not find an answer.")
                    citations = result.get("citations", [])

                    st.markdown(answer)
                    render_citations(citations, st)

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer,
                            "citations": citations,
                        }
                    )
                except Exception as err:
                    st.error(f"Something went wrong while checking document: {err}")
