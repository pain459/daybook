from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import re
import uuid

from .util import parse_due_token, parse_priority_token, parse_context_token, extract_id_token

TASK_LINE_RE = re.compile(r"^\s*-\s*\[(?P<mark>[ xX\-])\]\s+(?P<body>.+?)\s*$")
HEADING_RE = re.compile(r"^\s*#\s+(?P<h>.+?)\s*$")
FRONT_DATE_RE = re.compile(r"^\s*date:\s*(\d{4}-\d{2}-\d{2})\s*$")

@dataclass
class ParsedTask:
    id: str
    status: str              # open|done|dropped
    title: str
    details: str | None
    context: str | None
    priority: str | None
    due_date: str | None
    raw_line: str

@dataclass
class ParsedDocChunk:
    doc_id: str
    path: str
    doc_date: str | None
    section: str | None
    content: str

def _new_task_id() -> str:
    return "tsk_" + uuid.uuid4().hex[:8].upper()

def parse_markdown_file(path: str, today: date) -> tuple[list[ParsedTask], list[ParsedDocChunk], str | None, bool, str]:
    """
    Returns:
      tasks, doc_chunks, doc_date, did_rewrite, rewritten_text
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Try to extract doc_date from frontmatter or filename
    doc_date = None
    in_front = False
    for ln in lines[:30]:
        if ln.strip() == "---":
            in_front = not in_front
            continue
        if in_front:
            m = FRONT_DATE_RE.match(ln.strip())
            if m:
                doc_date = m.group(1)

    # Very lightweight section tracking
    current_section = None

    tasks: list[ParsedTask] = []
    doc_chunks: list[ParsedDocChunk] = []

    chunk_buf: list[str] = []
    chunk_section: str | None = None
    chunk_index = 0

    def flush_chunk():
        nonlocal chunk_index, chunk_buf, chunk_section
        content = "\n".join(chunk_buf).strip()
        if content:
            doc_id = f"{p.as_posix()}#{chunk_index}"
            doc_chunks.append(ParsedDocChunk(
                doc_id=doc_id,
                path=p.as_posix(),
                doc_date=doc_date,
                section=chunk_section,
                content=content
            ))
            chunk_index += 1
        chunk_buf = []
        chunk_section = current_section

    # We'll rewrite task lines to inject id:... if missing.
    did_rewrite = False
    out_lines: list[str] = []

    for ln in lines:
        hm = HEADING_RE.match(ln)
        if hm:
            flush_chunk()
            current_section = hm.group("h").strip()
            out_lines.append(ln)
            continue

        tm = TASK_LINE_RE.match(ln)
        if tm:
            mark = tm.group("mark")
            body = tm.group("body")
            status = "open"
            if mark.lower() == "x":
                status = "done"
            elif mark == "-":
                status = "dropped"

            tokens = body.split()
            tid = extract_id_token(tokens)

            # Remove known tokens from title rendering
            context = None
            priority = None
            due_date = None
            clean_parts: list[str] = []

            for t in tokens:
                if t.startswith("id:"):
                    continue
                c = parse_context_token(t)
                if c:
                    context = c
                    continue
                pr = parse_priority_token(t)
                if pr:
                    priority = pr
                    continue
                dd = parse_due_token(t, today)
                if dd:
                    due_date = dd
                    continue
                clean_parts.append(t)

            title = " ".join(clean_parts).strip()

            if not tid:
                tid = _new_task_id()
                # inject at end to keep it simple
                new_body = body + f" id:{tid}"
                ln = re.sub(r"\]\s+.+$", f"] {new_body}", ln)
                did_rewrite = True

            tasks.append(ParsedTask(
                id=tid,
                status=status,
                title=title,
                details=None,
                context=context,
                priority=priority,
                due_date=due_date,
                raw_line=ln
            ))

            out_lines.append(ln)
            # Also include tasks in doc chunks for retrieval
            chunk_buf.append(ln)
            continue

        # Normal text contributes to chunks
        out_lines.append(ln)
        chunk_buf.append(ln)

    flush_chunk()

    rewritten_text = "\n".join(out_lines) + ("\n" if text.endswith("\n") else "")
    return tasks, doc_chunks, doc_date, did_rewrite, rewritten_text
