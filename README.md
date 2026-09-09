# Legal AI

Upload any agreement, terms or contract and ask questions in simple words. It finds risky points like auto-renewal, rule changes without notice, data sharing, and hidden fees, with page and section numbers.

**Live App**: [leagal.streamlit.app](https://leagal.streamlit.app/)

**Stack**: Streamlit · LangGraph · Gemini (`gemini-3.6-flash` + `gemini-embedding-001`) · Chroma

## Setup

Need Python 3.12 and a Gemini API key.

```bash
uv venv --python 3.12 .venv && source .venv/bin/activate
uv pip install -e .
cp .env.example .env  # add GOOGLE_API_KEY=...
```

## Run

```bash
uv run streamlit run app.py
```

Open `http://localhost:8501` in your browser. Upload a PDF, DOCX or TXT file and start asking questions.