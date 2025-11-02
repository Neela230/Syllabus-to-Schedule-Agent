from __future__ import annotations

from pathlib import Path
from typing import List

import pdfplumber

from s2s.ingest import Document


def read_pdf(path: Path) -> Document:
    """Load a PDF syllabus and return a normalized Document."""
    pages: List[str] = []
    text_parts: List[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            pages.append(page_text)
            text_parts.append(page_text)
    text = "\n".join(text_parts)
    doc_id = Document.make_id(path, text)
    return Document(id=doc_id, path=str(path), text=text, pages=pages)
