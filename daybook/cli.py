from __future__ import annotations
import argparse
from datetime import date, datetime
from pathlib import Path
import os
import re

from dotenv import load_dotenv

from .db import connect, rebuild_docs_index
from .parser import parse_markdown_file
from .agenda import build_agenda_md
from .search import fts_search, fts_search_raw
from .llm import answer_with_context
from .util import ensure_dir, today_local

ROOT = Path(__file__).resolve().parent.parent
JOURNAL_DIR = ROOT / "journal"
NOTES_DIR = ROOT / "notes"
STATE_DIR = ROOT / "state"
DB_PATH = STATE_DIR / "daybook.db"

def daily_path(d: date) -> Path:
    return JOURNAL_DIR / f"{d.year:04d}/{d.month:02d}/{d.day:02d}.md"

def upsert_task(con, task, source_path: str, doc_date: str | None):
    now = datetime.now().isoformat(timespec="seconds")
    # Upsert task
    con.execute("""
      INSERT INTO tasks(id, title, details, context, priority, due_date, status, created_at, updated_at, last_seen_date)
      VALUES(?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(id) DO UPDATE SET
        title=excluded.title,
        context=COALESCE(excluded.context, tasks.context),
        priority=COALESCE(excluded.priority, tasks.priority),
        due_date=COALESCE(excluded.due_date, tasks.due_date),
        status=CASE
          WHEN excluded.status='done' THEN 'done'
          WHEN excluded.status='dropped' THEN 'dropped'
          ELSE tasks.status
        END,
        updated_at=excluded.updated_at,
        last_seen_date=excluded.last_seen_date
    """, (
        task.id,
        task.title,
        task.details,
        task.context,
        task.priority or "P2",
        task.due_date,
        task.status,
        now,
        now,
        doc_date
    ))

    # Add event
    con.execute("""
      INSERT INTO task_events(task_id, event_type, event_date, source_path, raw_line, created_at)
      VALUES(?,?,?,?,?,?)
    """, (task.id, task.status, doc_date or now[:10], source_path, task.raw_line, now))

def replace_agenda_block(text: str, agenda_md: str) -> str:
    """
    Replaces an existing '# Agenda (auto)' block if present, else inserts at top (after frontmatter if any).
    """
    lines = text.splitlines()
    # Find existing agenda start
    start = None
    for i, ln in enumerate(lines):
        if ln.strip() == "# Agenda (auto)":
            start = i
            break
    if start is not None:
        # Remove until next top-level heading that isn't agenda block itself
        end = start + 1
        while end < len(lines):
            if lines[end].startswith("# ") and lines[end].strip() != "# Agenda (auto)":
                break
            end += 1
        new_lines = lines[:start] + agenda_md.rstrip("\n").splitlines() + lines[end:]
        return "\n".join(new_lines).rstrip() + "\n"

    # Insert after frontmatter if present
    insert_at = 0
    if len(lines) >= 1 and lines[0].strip() == "---":
        # find closing ---
        for i in range(1, min(len(lines), 80)):
            if lines[i].strip() == "---":
                insert_at = i + 1
                break
    new_lines = lines[:insert_at] + [""] + agenda_md.rstrip("\n").splitlines() + [""] + lines[insert_at:]
    return "\n".join(new_lines).rstrip() + "\n"

def collect_md_files() -> list[Path]:
    files: list[Path] = []
    if JOURNAL_DIR.exists():
        files += list(JOURNAL_DIR.rglob("*.md"))
    if NOTES_DIR.exists():
        files += list(NOTES_DIR.rglob("*.md"))
    return sorted(files)

def cmd_sync(args):
    ensure_dir(str(STATE_DIR))
    con = connect(str(DB_PATH))
    today = today_local()

    # Rebuild docs index safely (keeps tasks)
    rebuild_docs_index(con)

    for fp in collect_md_files():
        tasks, chunks, doc_date, did_rewrite, rewritten = parse_markdown_file(str(fp), today)
        if did_rewrite:
            fp.write_text(rewritten, encoding="utf-8")

        for t in tasks:
            upsert_task(con, t, str(fp), doc_date)

        for ch in chunks:
            con.execute("""
              INSERT INTO docs(doc_id, path, doc_date, section, content)
              VALUES(?,?,?,?,?)
            """, (ch.doc_id, ch.path, ch.doc_date, ch.section, ch.content))

    con.commit()
    print(f"Synced {len(collect_md_files())} files into {DB_PATH}")

def cmd_open(args):
    ensure_dir(str(JOURNAL_DIR))
    today = today_local()
    fp = daily_path(today)
    fp.parent.mkdir(parents=True, exist_ok=True)

    if not fp.exists():
        fp.write_text(f"---\ndate: {today.isoformat()}\n---\n\n# Plan\n\n# Log\n\n# Learnings\n", encoding="utf-8")

    # sync first
    cmd_sync(args)

    # build agenda and inject
    con = connect(str(DB_PATH))
    agenda_md = build_agenda_md(con, today)

    text = fp.read_text(encoding="utf-8")
    new_text = replace_agenda_block(text, agenda_md)
    fp.write_text(new_text, encoding="utf-8")

    print(f"Opened day: {fp}")

def cmd_agenda(args):
    con = connect(str(DB_PATH))
    today = today_local()
    print(build_agenda_md(con, today))

def cmd_search(args):
    con = connect(str(DB_PATH))
    rows = fts_search(con, args.query, limit=args.limit)
    for r in rows:
        print(f"\n[{r['doc_id']}] {r['path']} (date={r['doc_date']}, section={r['section']})\n")
        # show a short excerpt
        content = r["content"]
        print(content[:800].rstrip())
        if len(content) > 800:
            print("...")


_STOPWORDS = {
    "what","did","i","learn","about","the","a","an","to","of","in","on","for","and","or",
    "is","are","was","were","it","this","that","with","from","when","how","why","tell",
    "me","my","we","you","today","yesterday","tomorrow"
}

def question_to_fts_expr(q: str) -> str:
    """
    Turn a natural-language question into an FTS5 expression that matches better.
    - removes stopwords
    - keeps keywords
    - uses prefix search (token*) to catch variants (concurrency -> concurrently)
    - joins with OR to avoid over-filtering
    """
    q = q.lower()
    # keep letters/numbers/_; split on everything else
    tokens = re.findall(r"\w+", q)
    keywords = [t for t in tokens if t not in _STOPWORDS and len(t) >= 3]

    # If nothing left, fall back to sanitized full query terms
    if not keywords:
        return ""

    # Prefix-match longer tokens for better recall
    terms = []
    for t in keywords[:8]:  # cap to avoid huge queries
        if len(t) >= 5:
            terms.append(f"{t}*")
        else:
            terms.append(t)

    # OR gives recall; we’ll rely on ranking + LLM to summarize
    return " OR ".join(terms)

def cmd_ask(args):
    load_dotenv()  # load OPENAI_API_KEY from .env
    con = connect(str(DB_PATH))
    expr = question_to_fts_expr(args.query)
    rows = fts_search_raw(con, expr, limit=args.k)

    if not rows:
        print("No local matches found.")
        return

    ctx = []
    for r in rows:
        ctx.append(f"[{r['doc_id']}]\n{r['content']}")

    ans = answer_with_context(args.query, ctx)
    print(ans)

def main():
    parser = argparse.ArgumentParser(prog="daybook")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_open = sub.add_parser("open", help="Create today's file (if missing), sync, and inject agenda.")
    p_open.set_defaults(func=cmd_open)

    p_sync = sub.add_parser("sync", help="Parse journal/notes into SQLite (tasks + docs index).")
    p_sync.set_defaults(func=cmd_sync)

    p_agenda = sub.add_parser("agenda", help="Print agenda to terminal.")
    p_agenda.set_defaults(func=cmd_agenda)

    p_search = sub.add_parser("search", help="Local full-text search over your notes/journal.")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=8)
    p_search.set_defaults(func=cmd_search)

    p_ask = sub.add_parser("ask", help="Retrieve locally then ask OpenAI using retrieved context.")
    p_ask.add_argument("query")
    p_ask.add_argument("--k", type=int, default=6, help="Top K local chunks to send as context.")
    p_ask.set_defaults(func=cmd_ask)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
