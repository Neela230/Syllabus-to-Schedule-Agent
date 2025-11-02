from __future__ import annotations

import json
from typing import Any, Dict, Tuple

import dateparser

from s2s.schemas import AssignmentRecord
from s2s.utils import log_interaction


def normalize_assignment(raw: Dict[str, Any], source_doc: str) -> Tuple[AssignmentRecord, Dict[str, Any]]:
    """Validate and normalize assignment JSON."""
    parsed_due = raw.get("due_datetime_iso")
    parsed_dt = dateparser.parse(parsed_due) if parsed_due else None
    if parsed_dt:
        raw["due_datetime_iso"] = parsed_dt.replace(microsecond=0).isoformat()
    raw["source_doc"] = source_doc
    if "confidence" not in raw:
        raw["confidence"] = 0.5
    record = AssignmentRecord(**raw)
    log_interaction(
        tag="assignment_normalize",
        prompt=json.dumps(raw),
        response="ok",
        metadata={"assignment_title": record.assignment_title},
    )
    return record, raw
