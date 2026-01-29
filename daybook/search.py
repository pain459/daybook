from __future__ import annotations
import sqlite3
import re

# For normal user search: strip punctuation that breaks MATCH syntax
_SANITIZE_RE = re.compile(r"[^\w\s]+")

def _sanitize_fts_query(q: str) -> str:
    q = q.strip()
    q = _SANITIZE_RE.sub(" ", q)      # remove ? " : etc.
    q = re.sub(r"\s+", " ", q).strip()
    return q if q else ""

def fts_search(con: sqlite3.Connection, query: str, limit: int = 8) -> list[sqlite3.Row]:
    """
    User-facing search. Sanitizes to avoid FTS syntax errors.
    """
    safe_q = _sanitize_fts_query(query)
    if not safe_q:
        return []

    sql = """
    SELECT d.doc_id, d.path, d.doc_date, d.section, d.content
    FROM docs_fts f
    JOIN docs d ON d.doc_id = f.doc_id
    WHERE docs_fts MATCH ?
    LIMIT ?
    """
    return list(con.execute(sql, (safe_q, limit)))

def fts_search_raw(con: sqlite3.Connection, match_expr: str, limit: int = 8) -> list[sqlite3.Row]:
    """
    Internal search. Expects a valid FTS5 MATCH expression (may include OR, AND, *).
    """
    match_expr = match_expr.strip()
    if not match_expr:
        return []

    sql = """
    SELECT d.doc_id, d.path, d.doc_date, d.section, d.content
    FROM docs_fts f
    JOIN docs d ON d.doc_id = f.doc_id
    WHERE docs_fts MATCH ?
    LIMIT ?
    """
    return list(con.execute(sql, (match_expr, limit)))
