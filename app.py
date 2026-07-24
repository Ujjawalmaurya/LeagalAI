from __future__ import annotations

import os
import streamlit as st
from dotenv import load_dotenv

from src.config import AppConfig
from src.document_loader import extract_documents_from_upload, split_legal_documents
from src.graph import run_legal_analysis
from src.vectorstore import clear_vectorstore, index_documents

# Ensure latest .env is loaded
load_dotenv(override=True)

st.set_page_config(
    page_title="Legal AI",
    layout="centered",
    initial_sidebar_state="auto",
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_doc_name" not in st.session_state:
    st.session_state.active_doc_name = None
if "indexed_chunks_count" not in st.session_state:
    st.session_state.indexed_chunks_count = 0
if "prompt_to_submit" not in st.session_state:
    st.session_state.prompt_to_submit = None

# Resolve key directly from environment
api_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()

# Sidebar: Document upload and model options
with st.sidebar:
    st.subheader("Document")
    uploaded_file = st.file_uploader(
        "Upload agreement",
        type=["pdf", "docx", "txt", "md"],
        label_visibility="collapsed",
    )

    if not api_key:
        st.warning("No GOOGLE_API_KEY found in your environment or .env file.")

    with st.expander("Model Options"):
        model_choice = st.selectbox(
            "Chat Model",
            options=["gemini-3.6-flash", "gemini-2.5-flash", "gemini-1.5-pro"],
            index=0,
        )
        embedding_choice = st.selectbox(
            "Embedding Model",
            options=["gemini-embedding-001", "gemini-embedding-2-preview"],
            index=0,
        )

    # File indexing
    if uploaded_file is not None:
        file_name = uploaded_file.name
        is_new_file = st.session_state.active_doc_name != file_name

        if is_new_file:
            if st.button("Index document", type="primary", use_container_width=True):
                if not api_key:
                    st.error("Cannot index: GOOGLE_API_KEY is not set in environment or .env.")
                else:
                    with st.status("Reading and indexing document...", expanded=True) as status:
                        try:
                            cfg = AppConfig(
                                gemini_api_key=api_key,
                                chat_model=model_choice,
                                embedding_model=embedding_choice,
                            )
                            clear_vectorstore(cfg)

                            file_bytes = uploaded_file.read()
                            raw_docs = extract_documents_from_upload(file_bytes, file_name)

                            if not raw_docs:
                                status.update(label="No readable text found in file.", state="error")
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
        if st.button("Clear document", use_container_width=True):
            cfg = AppConfig(gemini_api_key=api_key, embedding_model=embedding_choice)
            clear_vectorstore(cfg)
            st.session_state.active_doc_name = None
            st.session_state.indexed_chunks_count = 0
            st.session_state.messages = []
            st.rerun()


current_config = AppConfig(
    gemini_api_key=api_key,
    chat_model=model_choice if "model_choice" in locals() else "gemini-3.6-flash",
    embedding_model=embedding_choice if "embedding_choice" in locals() else "gemini-embedding-001",
)

# Main screen
st.title("Legal AI")
st.caption("Spot hidden risks, unfair clauses, and confusing terms in plain English.")

# Prompt shortcuts when document is ready but chat is empty
if st.session_state.active_doc_name and not st.session_state.messages:
    st.write("Common questions you can ask:")
    sample_queries = [
        "What are the biggest hidden risks or unfair terms here?",
        "Can they change the terms or pricing without notifying me?",
        "How do I cancel this, and will it auto-renew?",
        "What personal data is collected and who is it shared with?",
    ]
    for q in sample_queries:
        if st.button(q, key=f"q_{q}", use_container_width=True):
            st.session_state.prompt_to_submit = q
            st.rerun()

elif not st.session_state.active_doc_name:
    st.info("Upload a PDF, DOCX, or TXT agreement in the sidebar to get started.")

def clean_chat_text(val: Any) -> str:
    if isinstance(val, str) and (val.startswith("[{'type': 'text'") or val.startswith('[{"type": "text"')):
        try:
            import ast
            parsed = ast.literal_eval(val)
            if isinstance(parsed, list):
                chunks = [b.get("text", "") for b in parsed if isinstance(b, dict) and "text" in b]
                if chunks:
                    return "\n".join(chunks).strip()
        except Exception:
            pass
    return str(val) if val is not None else ""


# Render message history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(clean_chat_text(msg["content"]))

        citations = msg.get("citations", [])
        if citations:
            with st.expander(f"Referenced clauses ({len(citations)})"):
                for cite in citations:
                    ref_idx = cite.get("ref", 1)
                    source = cite.get("source", "Document")
                    page = cite.get("page", 1)
                    text = cite.get("full_text", "").strip()

                    st.markdown(f"**Clause {ref_idx}** (Page {page}, `{source}`)")
                    st.markdown(f"> {text}")
                    st.write("")


# Chat input handling
user_input = st.chat_input("Ask a question about this document...")

if st.session_state.prompt_to_submit:
    user_input = st.session_state.prompt_to_submit
    st.session_state.prompt_to_submit = None

if user_input:
    if not current_config.gemini_api_key:
        st.error("GOOGLE_API_KEY is not set in your environment or .env file.")
    elif not st.session_state.active_doc_name:
        st.warning("Upload a document in the sidebar first.")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Looking through the agreement..."):
                try:
                    result = run_legal_analysis(user_input, config=current_config)
                    answer = result.get("answer", "No answer could be generated.")
                    citations = result.get("citations", [])

                    st.markdown(answer)

                    if citations:
                        with st.expander(f"Referenced clauses ({len(citations)})"):
                            for cite in citations:
                                ref_idx = cite.get("ref", 1)
                                source = cite.get("source", "Document")
                                page = cite.get("page", 1)
                                text = cite.get("full_text", "").strip()

                                st.markdown(f"**Clause {ref_idx}** (Page {page}, `{source}`)")
                                st.markdown(f"> {text}")
                                st.write("")

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer,
                            "citations": citations,
                        }
                    )
                except Exception as err:
                    st.error(f"Error checking document: {err}")
