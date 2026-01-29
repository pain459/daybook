# Daybook  
*A plain-text daily planner, diary, and personal knowledge base — powered by local search and optional LLM assistance.*

---

## What is Daybook?

Daybook is a **human-first personal assistant** built on simple Markdown files and a small local parser.

You:
- write daily plans, logs, and learnings in plain text
- never touch JSON, databases, or UI
- use a CLI to build agendas, carry tasks forward, and retrieve information on demand

Daybook turns your **daily writing** into:
- a **planner** (what to do today)
- a **diary** (what happened)
- a **knowledge base** (what you learned and decided)

All data lives locally.  
Nothing is hidden behind an app or proprietary format.

---

## Core principles

- **Plain text is the source of truth**
- **No frontend required**
- **Low syntax burden**
- **Rebuildable state**
- **LLM is optional and secondary**

If the database is deleted, your Markdown files are still complete.

---

## High-level architecture

Markdown files (journal/, notes/)  
→ Parser (forgiving, token-based)  
→ SQLite (tasks + full-text index)  
→ CLI commands  
→ (Optional) OpenAI LLM for summaries & Q&A  

---

## Repository structure

daybook/
├── README.md
├── .env.example
├── requirements.txt
│
├── daybook/
│   ├── cli.py
│   ├── parser.py
│   ├── agenda.py
│   ├── search.py
│   ├── db.py
│   ├── llm.py
│   └── util.py
│
├── journal/
│   └── YYYY/MM/DD.md
│
├── notes/
│
└── state/
    └── daybook.db

---

## Requirements

- Python 3.10+
- SQLite (bundled with Python; FTS5 recommended)
- Optional: OpenAI API key (for ask)

---

## Setup

### 1. Clone and create a virtual environment

python -m venv .venv  
source .venv/bin/activate

### 2. Install dependencies

pip install -r requirements.txt

### 3. (Optional) Configure OpenAI

Copy the example file:

cp .env.example .env

Edit `.env`:

OPENAI_API_KEY=your_api_key_here  
OPENAI_MODEL=gpt-5.2

If you skip this, Daybook still works fully — only the `ask` command is disabled.

---

## Daily usage flow

### Morning — start the day

python -m daybook.cli open

Creates today’s journal file (if missing), syncs state, and injects an auto agenda.

### During the day — write naturally

Example:

# Plan
- [ ] Review incident RCA draft @work p:P0 due:today
- [ ] Pay electricity bill @personal p:P1 due:2026-01-30

# Log
09:20 Debugged VS Code remote auth failure

# Learnings
- Kerberos refresh fails if kinit principal is incorrect

### End of day — close the loop

python -m daybook.cli close

Generates a short summary under `# Summary (auto)`.

---

## Tasks

- [ ] open
- [x] done
- [-] dropped

Optional tokens:
- @work / @personal
- p:P0 – p:P3
- due:today / due:YYYY-MM-DD

Tasks automatically receive stable IDs.

---

## Notes

Use `notes/` for reusable knowledge.

Rule:
If you search for something twice, promote it to a note.

---

## Search

Local search:

python -m daybook.cli search "kerberos"

LLM-assisted recall:

python -m daybook.cli ask "What did I learn about kinit refresh?"

---

## Rebuilding state

rm -f state/daybook.db  
python -m daybook.cli sync

---

## Design decisions

- Markdown over JSON
- SQLite over vector DBs
- Parser over strict schemas
- LLM as interpreter, not memory

---

## Typical commands

python -m daybook.cli open  
python -m daybook.cli close  
python -m daybook.cli sync  
python -m daybook.cli search  
python -m daybook.cli ask  

---

## Philosophy

Write once.  
Refine once.  
Then stop remembering.
