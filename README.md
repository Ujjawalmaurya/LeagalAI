# Legal AI

Upload a Terms of Service, Privacy Policy or contract and ask questions in plain English. Flags hidden risks like arbitration clauses, auto-renewals, unilateral changes, data sharing with exact page and clause citations.

**Stack**: Streamlit · LangGraph · Gemini (`gemini-2.0-flash` + `gemini-embedding-001`) · Chroma

## Setup

Requires Python 3.11–3.12 and a Gemini API key

```bash
uv venv --python 3.12 .venv && source .venv/bin/activate
uv pip install -e .
cp .env.example .env  # add GOOGLE_API_KEY=...
```

## Run

```bash
uv run streamlit run app.py
```

Opens at `http://localhost:8501`. Upload a PDF, DOCX or TXT, then just ask.