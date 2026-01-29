from __future__ import annotations
import sqlite3
from pathlib import Path

TASKS_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  details TEXT,
  context TEXT,
  priority TEXT DEFAULT 'P2',
  due_date TEXT,
  status TEXT NOT NULL DEFAULT 'open', -- open|done|dropped
  created_at TEXT,
  updated_at TEXT,
  last_seen_date TEXT
);

CREATE TABLE IF NOT EXISTS task_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT NOT NULL,
  event_type TEXT NOT NULL, -- seen|done|dropped
  event_date TEXT NOT NULL,
  source_path TEXT NOT NULL,
  raw_line TEXT,
  created_at TEXT NOT NULL
);
"""

DOCS_SCHEMA = """
CREATE TABLE IF NOT EXISTS docs (
  doc_id TEXT PRIMARY KEY,      -- e.g. path#chunk_index
  path TEXT NOT NULL,
  doc_date TEXT,                -- extracted from frontmatter or filename if possible
  section TEXT,
  content TEXT NOT NULL
);

-- Full-text index on content
CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
  doc_id,
  content,
  tokenize = 'unicode61'
);

CREATE TRIGGER IF NOT EXISTS docs_ai AFTER INSERT ON docs BEGIN
  INSERT INTO docs_fts(doc_id, content) VALUES (new.doc_id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS docs_ad AFTER DELETE ON docs BEGIN
  INSERT INTO docs_fts(docs_fts, doc_id, content) VALUES('delete', old.doc_id, old.content);
END;

CREATE TRIGGER IF NOT EXISTS docs_au AFTER UPDATE ON docs BEGIN
  INSERT INTO docs_fts(docs_fts, doc_id, content) VALUES('delete', old.doc_id, old.content);
  INSERT INTO docs_fts(doc_id, content) VALUES (new.doc_id, new.content);
END;
"""

def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.executescript(TASKS_SCHEMA)
    con.executescript(DOCS_SCHEMA)
    return con

def rebuild_docs_index(con: sqlite3.Connection) -> None:
    """
    Drops and recreates docs + FTS + triggers.
    Keeps tasks tables intact.
    """
    con.executescript("""
    DROP TRIGGER IF EXISTS docs_ai;
    DROP TRIGGER IF EXISTS docs_ad;
    DROP TRIGGER IF EXISTS docs_au;
    DROP TABLE IF EXISTS docs_fts;
    DROP TABLE IF EXISTS docs;
    """)
    con.executescript(DOCS_SCHEMA)
