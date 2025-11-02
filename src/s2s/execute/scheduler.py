from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from s2s.schemas import AssignmentRecord, Task


def schedule_tasks(assignment: AssignmentRecord, tasks: List[Task]) -> List[Task]:
    """Backward schedule tasks relative to assignment due date."""
    due = assignment.due_datetime()
    scheduled: List[Task] = []
    next_due = due
    for task in reversed(tasks):
        duration = timedelta(hours=task.hours_estimate)
        start = next_due - duration
        scheduled.append(
            Task(
                title=task.title,
                hours_estimate=task.hours_estimate,
                earliest_start_iso=start.isoformat(),
                due_iso=next_due.isoformat(),
                depends_on=task.depends_on,
            )
        )
        next_due = start
    return list(reversed(scheduled))
