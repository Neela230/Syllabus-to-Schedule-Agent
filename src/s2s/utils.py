from __future__ import annotations

import json
import os
from datetime import datetime
from hashlib import sha1
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

LOG_DIR = Path(os.getenv("S2S_LOG_DIR", "logs"))
LOG_FILE = LOG_DIR / "interactions.log"


def ensure_dir(path: Path) -> Path:
    """Create path if missing and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_interaction(tag: str, prompt: str, response: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Persist a prompt/response pair for traceability."""
    ensure_dir(LOG_DIR)
    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "tag": tag,
        "prompt": prompt,
        "response": response,
        "metadata": metadata or {},
    }
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read a JSONL file into memory."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    """Write iterable of dicts to JSONL."""
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def chunk_text(text: str, max_chars: int = 800, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks for RAG ingestion."""
    cleaned = text.replace("\r", " ").replace("\n", " ").split()
    chunks: List[str] = []
    current: List[str] = []
    total = 0
    for token in cleaned:
        current.append(token)
        total += len(token) + 1
        if total >= max_chars:
            chunk = " ".join(current)
            chunks.append(chunk)
            overlap_tokens = chunk.split()[-overlap:] if overlap and len(current) > overlap else []
            current = list(overlap_tokens)
            total = sum(len(tok) + 1 for tok in current)
    if current:
        chunks.append(" ".join(current))
    return chunks


def safe_filename(text: str) -> str:
    """Return a filesystem-safe identifier derived from text."""
    digest = sha1(text.encode("utf-8")).hexdigest()[:12]
    return digest


def hash_text(text: str) -> str:
    """Return a stable hash for supplied text."""
    return sha1(text.encode("utf-8")).hexdigest()
