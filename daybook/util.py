from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
import os
import re

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def today_local() -> date:
    # Your timezone is Asia/Kolkata; rely on system time here.
    return date.today()

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def iso_today() -> str:
    return today_local().isoformat()

def parse_due_token(token: str, today: date) -> str | None:
    # due:today or due:YYYY-MM-DD
    if not token.startswith("due:"):
        return None
    v = token.split(":", 1)[1].strip()
    if v == "today":
        return today.isoformat()
    if DATE_RE.match(v):
        return v
    return None

def parse_priority_token(token: str) -> str | None:
    # p:P0..P3
    if not token.startswith("p:"):
        return None
    v = token.split(":", 1)[1].strip().upper()
    if v in {"P0", "P1", "P2", "P3"}:
        return v
    return None

def parse_context_token(token: str) -> str | None:
    # @work / @personal
    if token.startswith("@") and len(token) > 1:
        return token[1:].lower()
    return None

def extract_id_token(tokens: list[str]) -> str | None:
    for t in tokens:
        if t.startswith("id:") and len(t) > 3:
            return t.split(":", 1)[1].strip()
    return None
