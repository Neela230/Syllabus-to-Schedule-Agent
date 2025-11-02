from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import List, Optional

from transformers import pipeline

from s2s.schemas import AssignmentRecord, Task
from s2s.utils import log_interaction


class TaskPlanner:
    """Generate milestone tasks for an assignment."""

    def __init__(self, planner_model: Optional[str] = None) -> None:
        model_name = planner_model or os.getenv("S2S_PLANNER_MODEL")
        if model_name:
            self.generator = pipeline("text2text-generation", model=model_name)
        else:
            self.generator = None

    def plan(self, assignment: AssignmentRecord) -> List[Task]:
        due = assignment.due_datetime()
        hours = self._estimate_hours(assignment)
        tasks = self._llm_plan(assignment, hours) if self.generator else self._heuristic_plan(assignment, hours)
        tasks = self._ensure_schedule(tasks, due)
        log_interaction(
            tag="planner_plan",
            prompt=json.dumps(assignment.dict_for_storage()),
            response=json.dumps([t.dict_for_storage() for t in tasks]),
            metadata={"hours": hours},
        )
        return tasks

    def _estimate_hours(self, assignment: AssignmentRecord) -> float:
        base = 6.0
        if assignment.deliverables:
            base += 2.0 * len(assignment.deliverables)
        if assignment.points_or_weight:
            if "%" in assignment.points_or_weight:
                try:
                    pct = float(assignment.points_or_weight.replace("%", "").strip())
                    base += pct / 10.0
                except ValueError:
                    pass
            elif any(char.isdigit() for char in assignment.points_or_weight):
                digits = "".join(filter(str.isdigit, assignment.points_or_weight))
                if digits:
                    base += min(10.0, float(digits) / 5.0)
        return max(2.0, min(40.0, base))

    def _heuristic_plan(self, assignment: AssignmentRecord, hours: float) -> List[Task]:
        segments = [
            ("Review requirements", 0.2),
            ("Research & outline", 0.3),
            ("Draft deliverables", 0.35),
            ("Quality review & submit", 0.15),
        ]
        tasks: List[Task] = []
        cumulative = 0.0
        for title_suffix, portion in segments:
            share = round(hours * portion, 1)
            share = max(0.5, share)
            cumulative += share
            title = f"{assignment.assignment_title}: {title_suffix}"
            depends = [tasks[-1].title] if tasks else []
            tasks.append(
                Task(
                    title=title,
                    hours_estimate=share,
                    due_iso=assignment.due_datetime_iso,
                    depends_on=depends,
                )
            )
        adjustment = hours - cumulative
        if tasks and abs(adjustment) > 0.2:
            tasks[-1].hours_estimate = round(tasks[-1].hours_estimate + adjustment, 1)
        return tasks

    def _llm_plan(self, assignment: AssignmentRecord, hours: float) -> List[Task]:  # pragma: no cover
        prompt = (
            "Create 3-5 milestone tasks for this assignment. "
            "Respond as JSON list with objects {title,hours_estimate,depends_on}. "
            f"Total hours should be about {hours:.1f}.\n"
            f"Assignment: {json.dumps(assignment.dict_for_storage())}"
        )
        raw = self.generator(prompt, max_length=256)[0]["generated_text"]
        log_interaction("planner_llm_prompt", prompt, raw)
        try:
            data = json.loads(raw)
            tasks: List[Task] = []
            for item in data:
                tasks.append(
                    Task(
                        title=item.get("title", assignment.assignment_title),
                        hours_estimate=float(item.get("hours_estimate", hours / max(len(data), 1))),
                        due_iso=assignment.due_datetime_iso,
                        depends_on=item.get("depends_on", []),
                    )
                )
            return tasks
        except Exception:
            return self._heuristic_plan(assignment, hours)

    def _ensure_schedule(self, tasks: List[Task], due: datetime) -> List[Task]:
        scheduled: List[Task] = []
        current_due = due
        for task in reversed(tasks):
            span = timedelta(hours=task.hours_estimate)
            start = current_due - span
            scheduled.append(
                Task(
                    title=task.title,
                    hours_estimate=task.hours_estimate,
                    earliest_start_iso=start.isoformat(),
                    due_iso=current_due.isoformat(),
                    depends_on=task.depends_on,
                )
            )
            current_due = start
        scheduled.reverse()
        return scheduled
