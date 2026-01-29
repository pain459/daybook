# Daybook (plain-text diary + planner + local search + LLM answers)

Daybook is a small assistant for day-to-day planning + remembering facts.
You edit Markdown files. Daybook parses them into a local SQLite database and:
- builds your morning agenda from pending tasks (overdue, priority, age)
- lets you search your own notes/journal using local full-text search (FTS)
- optionally asks an OpenAI model to answer questions using retrieved context (RAG-style)

## 1) Setup

### Requirements
- Python 3.10+
- SQLite (bundled with Python; FTS5 usually enabled by default)

### Install
```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
