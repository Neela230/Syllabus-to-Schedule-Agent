from __future__ import annotations

import csv
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Tuple

from s2s.schemas import AssignmentRecord, Task
from s2s.utils import ensure_dir


def write_calendar_ics(
    items: Iterable[Tuple[AssignmentRecord, List[Task]]],
    output_dir: Path = Path("out"),
    filename: str = "calendar.ics",
) -> Path:
    """Export assignments and tasks as ICS events."""
    ensure_dir(output_dir)
    path = output_dir / filename
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//S2S Agent//EN",
    ]
    for assignment, tasks in items:
        event_uid = getattr(assignment, "id", assignment.assignment_title)
        lines.extend(_ics_event(assignment.assignment_title, assignment.due_datetime_iso, event_uid))
        for task in tasks:
            lines.extend(
                _ics_event(
                    task.title,
                    task.due_iso,
                    f"{event_uid}-{task.title}",
                    start_iso=task.earliest_start_iso,
                )
            )
    lines.append("END:VCALENDAR")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _ics_event(title: str, due_iso: str, uid: str, start_iso: str | None = None) -> List[str]:
    start = start_iso or due_iso
    return [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{_ics_datetime(datetime.utcnow().isoformat())}",
        f"DTSTART:{_ics_datetime(start)}",
        f"DTEND:{_ics_datetime(due_iso)}",
        f"SUMMARY:{title}",
        "END:VEVENT",
    ]


def _ics_datetime(value: str) -> str:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.strftime("%Y%m%dT%H%M%SZ")


def write_tasks_csv(
    items: Iterable[Tuple[AssignmentRecord, List[Task]]],
    output_dir: Path = Path("out"),
    filename: str = "tasks.csv",
) -> Path:
    ensure_dir(output_dir)
    path = output_dir / filename
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["course", "assignment", "task", "start_iso", "due_iso", "hours", "depends_on"])
        for assignment, tasks in items:
            for task in tasks:
                writer.writerow(
                    [
                        assignment.course or "",
                        assignment.assignment_title,
                        task.title,
                        task.earliest_start_iso or "",
                        task.due_iso,
                        task.hours_estimate,
                        ";".join(task.depends_on),
                    ]
                )
    return path


def write_sqlite(
    items: Iterable[Tuple[AssignmentRecord, List[Task]]],
    output_path: Path = Path("out/tasks.db"),
) -> Path:
    ensure_dir(output_path.parent)
    conn = sqlite3.connect(str(output_path))
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            course TEXT,
            assignment TEXT,
            task TEXT,
            start_iso TEXT,
            due_iso TEXT,
            hours REAL,
            depends_on TEXT
        )
        """
    )
    cur.execute("DELETE FROM tasks")
    for assignment, tasks in items:
        for task in tasks:
            cur.execute(
                "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    assignment.course,
                    assignment.assignment_title,
                    task.title,
                    task.earliest_start_iso,
                    task.due_iso,
                    task.hours_estimate,
                    ";".join(task.depends_on),
                ),
            )
    conn.commit()
    conn.close()
    return output_path
