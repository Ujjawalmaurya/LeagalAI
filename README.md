# Legal AI

Helps you read Terms of Service, Privacy Policies, and contracts without getting lost in legal jargon. Upload an agreement, ask questions, and get plain-English explanations that flag hidden risks like unilateral changes, arbitration clauses, auto-renewals, and data sharing.

## How it works

1. **Ingestion**: Reads PDF, DOCX, or TXT agreements and chunks them along legal section boundaries (`Section`, `Article`, `§`) while preserving page numbers.
2. **Indexing**: Embeds chunks using Gemini (`gemini-embedding-001`) into a local Chroma vector store.
3. **Retrieval**: Uses Maximal Marginal Relevance (MMR) so you get diverse clauses instead of five copies of the same boilerplate.
4. **Analysis**: Runs through a LangGraph workflow that prompts Gemini to unpack the clauses, highlight gotchas, and cite exact page and clause numbers.

## Setup

Requires Python 3.11 or 3.12 (managed via `uv`) and a Gemini API key from [Google AI Studio](https://aistudio.google.com/).

```bash
# Create virtual environment and install dependencies
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -e .

# Configure API key
cp .env.example .env
# Add your key to .env: GOOGLE_API_KEY=...
```

## Run

```bash
uv run streamlit run app.py
```

Open `http://localhost:8501`.