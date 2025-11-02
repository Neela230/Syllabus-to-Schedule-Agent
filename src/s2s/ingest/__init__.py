from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from s2s.utils import hash_text


@dataclass
class Document:
    """Normalized document used across the pipeline."""

    id: str
    path: str
    text: str
    pages: List[str]

    def to_dict(self) -> Dict[str, str]:
        return {
            "id": self.id,
            "path": self.path,
            "text": self.text,
            "pages": self.pages,
        }

    @staticmethod
    def make_id(path: Path, text: str) -> str:
        return hash_text(f"{path}-{len(text)}")

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "Document":
        return cls(
            id=data["id"],
            path=data["path"],
            text=data["text"],
            pages=data.get("pages", []),
        )
