from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from s2s.ingest import Document


def read_html_or_text(path: Path) -> Document:
    """Parse HTML or plaintext announcements into Document objects."""
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".html", ".htm"}:
        soup = BeautifulSoup(raw, "html.parser")
        text = soup.get_text(separator="\n")
    else:
        text = raw
    doc_id = Document.make_id(path, text)
    return Document(id=doc_id, path=str(path), text=text, pages=[text])
