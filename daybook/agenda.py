from __future__ import annotations
import sqlite3
from datetime import date, datetime

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

def _age_days(created_at: str | None, today: date) -> int:
    if not created_at:
        return 0
    try:
        d = datetime.fromisoformat(created_at).date()
        return (today - d).days
    except Exception:
        return 0

def fetch_open_tasks(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(con.execute("""
      SELECT * FROM tasks
      WHERE status = 'open'
    """))

def build_agenda_md(con: sqlite3.Connection, today: date) -> str:
    rows = fetch_open_tasks(con)

    items = []
    for r in rows:
        due = r["due_date"]
        pr = (r["priority"] or "P2").upper()
        age = _age_days(r["created_at"], today)
        overdue = 1 if (due and due < today.isoformat()) else 0
        items.append((overdue, PRIORITY_ORDER.get(pr, 2), due or "9999-12-31", -age, r))

    items.sort()

    overdue_list = []
    p0_today = []
    stale = []
    rest = []

    for overdue, pr_ord, due_key, neg_age, r in items:
        due = r["due_date"]
        pr = (r["priority"] or "P2").upper()
        age = -neg_age
        line = f"- [ ] {r['title']}"
        if r["context"]:
            line += f" @{r['context']}"
        line += f" p:{pr}"
        if due:
            line += f" due:{due}"
        line += f" id:{r['id']}"

        if due == today.isoformat() and pr == "P0":
            p0_today.append(line)
        elif overdue:
            overdue_list.append(line)
        elif age >= 7:
            stale.append(line)
        else:
            rest.append(line)

    out = []
    out.append("# Agenda (auto)")
    if p0_today:
        out.append("## P0 Today")
        out.extend(p0_today)
        out.append("")
    if overdue_list:
        out.append("## Overdue")
        out.extend(overdue_list)
        out.append("")
    if stale:
        out.append("## Stale (7+ days)")
        out.extend(stale)
        out.append("")
    if rest:
        out.append("## Open")
        out.extend(rest)
        out.append("")
    return "\n".join(out).rstrip() + "\n"
