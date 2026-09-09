from __future__ import annotations

import io
from typing import BinaryIO, Sequence

from docx import Document as DocxDocument
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


def load_pdf_file(file_obj: BinaryIO | bytes, source_name: str) -> list[Document]:
    # Read page by page so we can show exact page numbers
    reader = PdfReader(io.BytesIO(file_obj) if isinstance(file_obj, bytes) else file_obj)

    docs: list[Document] = []
    for idx, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        if text:
            docs.append(
                Document(
                    page_content=text,
                    metadata={"source": source_name, "page": idx + 1},
                )
            )
    return docs


def load_docx_file(file_obj: BinaryIO | bytes, source_name: str) -> list[Document]:
    doc = DocxDocument(io.BytesIO(file_obj) if isinstance(file_obj, bytes) else file_obj)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    full_text = "\n\n".join(paragraphs)

    if not full_text:
        return []

    return [Document(page_content=full_text, metadata={"source": source_name, "page": 1})]


def load_text_file(content: str | bytes, source_name: str) -> list[Document]:
    # Ignore broken characters so reading text does not fail
    text = (
        content.decode("utf-8", errors="replace").strip()
        if isinstance(content, bytes)
        else content.strip()
    )

    if not text:
        return []

    return [Document(page_content=text, metadata={"source": source_name, "page": 1})]


def extract_documents_from_upload(file_bytes: bytes, filename: str) -> list[Document]:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return load_pdf_file(file_bytes, source_name=filename)
    if lower.endswith(".docx"):
        return load_docx_file(file_bytes, source_name=filename)
    if lower.endswith(".txt") or lower.endswith(".md"):
        return load_text_file(file_bytes, source_name=filename)

    raise ValueError(f"File type not supported for '{filename}'. Please use PDF, DOCX, or TXT.")


def split_legal_documents(
    documents: Sequence[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[Document]:
    # Split by sections and articles first before cutting normal sentences
    legal_separators = [
        "\n\nSection ",
        "\n\nARTICLE ",
        "\n\nArticle ",
        "\n\nClause ",
        "\n\n§",
        "\n\n",
        "\n",
        ". ",
        " ",
        "",
    ]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=legal_separators,
    )

    chunks = splitter.split_documents(list(documents))
    for idx, chunk in enumerate(chunks, start=1):
        chunk.metadata["chunk_index"] = idx

    return chunks
