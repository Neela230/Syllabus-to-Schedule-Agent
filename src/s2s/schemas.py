from __future__ import annotations

from datetime import datetime
from typing import List, Optional

try:  # pragma: no cover - compatibility shim
    from pydantic import BaseModel, Field, field_validator
except ImportError:  # Pydantic v1 fallback
    from pydantic import BaseModel, Field, validator as field_validator  # type: ignore


class S2SBaseModel(BaseModel):
    """Compatibility layer across Pydantic v1/v2."""

    def as_dict(self) -> dict:
        if hasattr(self, "model_dump"):
            return getattr(self, "model_dump")()
        return self.dict()


class AssignmentRecord(S2SBaseModel):
    """Structure extracted from syllabi."""

    course: Optional[str] = Field(default=None, description="Course title")
    assignment_title: str = Field(..., description="Assignment name")
    due_datetime_iso: str = Field(..., description="ISO8601 due datetime")
    deliverables: List[str] = Field(default_factory=list, description="Submission artifacts")
    points_or_weight: Optional[str] = Field(default=None, description="Score or weight")
    source_doc: str = Field(..., description="Originating document path")
    evidence_spans: List[str] = Field(default_factory=list, description="Supporting snippets")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Extractor confidence")

    @field_validator("due_datetime_iso")
    def validate_iso(cls, value: str) -> str:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    def due_datetime(self) -> datetime:
        return datetime.fromisoformat(self.due_datetime_iso.replace("Z", "+00:00"))

    def dict_for_storage(self) -> dict:
        return self.as_dict()


class Task(S2SBaseModel):
    """Planner milestone tasks."""

    title: str
    hours_estimate: float = Field(..., ge=0.25, description="Estimated effort in hours")
    earliest_start_iso: Optional[str] = Field(default=None)
    due_iso: str
    depends_on: List[str] = Field(default_factory=list)

    @field_validator("due_iso")
    def validate_due(cls, value: str) -> str:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    def dict_for_storage(self) -> dict:
        return self.as_dict()
