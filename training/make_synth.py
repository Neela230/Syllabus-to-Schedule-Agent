#!/usr/bin/env python3
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

COURSES = [
    "Intro to Robotics",
    "Human-Computer Interaction",
    "Bioinformatics",
    "Digital Signal Processing",
    "Applied Ethics",
    "Game Design",
    "Computational Linguistics",
    "Environmental Science",
    "Financial Modeling",
    "Health Informatics",
    "Data Visualization",
    "Cloud Computing",
    "Cybersecurity",
    "Educational Psychology",
    "Media Studies",
    "Urban Planning",
]

DELIVERABLE_TEMPLATES: List[List[str]] = [
    ["Report PDF"],
    ["Slide deck", "Presentation video"],
    ["Notebook", "Dataset"],
    ["Reflection essay"],
    ["Prototype", "User testing notes"],
    ["Poster PDF"],
    ["Code repository", "README"],
]

SPAN_TEMPLATE = "Assignment {title} is due {date} at {time}."


def _random_due(base_date: datetime) -> datetime:
    return base_date + timedelta(days=random.randint(5, 80), hours=random.choice([9, 17, 23]))


def _render(course: str, title: str, due: datetime, deliverables: List[str], weight: str) -> Tuple[str, dict]:
    input_text = (
        f"Syllabus snippet: Course={course}. Assignment {title} is due {due.strftime('%b %d %Y')} "
        f"at {due.strftime('%H:%M')}. Submit {', '.join(deliverables)}. Weight: {weight}."
    )
    target = {
        "course": course,
        "assignment_title": title,
        "due_datetime_iso": due.replace(microsecond=0).isoformat(),
        "deliverables": deliverables,
        "points_or_weight": weight,
        "source_doc": "synth",
        "evidence_spans": [
            SPAN_TEMPLATE.format(title=title, date=due.strftime("%b %d %Y"), time=due.strftime("%H:%M"))
        ],
        "confidence": 0.9,
    }
    return input_text, target


def main(count: int = 150, seed: int = 1337) -> None:
    random.seed(seed)
    out_path = Path("training/data/synth.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    base = datetime(2024, 1, 15)
    for idx in range(count):
        course = random.choice(COURSES)
        title = f"{random.choice(['Project', 'Assignment', 'Lab', 'Presentation', 'Memo', 'Quiz'])} {idx + 1}"
        deliverables = random.choice(DELIVERABLE_TEMPLATES)
        due = _random_due(base)
        weight = random.choice(["5%", "8%", "10%", "12%", "15%", "20%", "30 pts", "40 pts"])
        input_text, target = _render(course, title, due, deliverables, weight)
        records.append({"input_text": input_text, "target_json": json.dumps(target)})
    with out_path.open("w", encoding="utf-8") as handle:
        for row in records:
            handle.write(json.dumps(row) + "\n")
    print(f"Wrote {len(records)} synthetic samples to {out_path}")


if __name__ == "__main__":
    main()
