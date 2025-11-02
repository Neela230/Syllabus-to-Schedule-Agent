from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Dict, Any

import pydantic  # ensure compatibility with chromadb on pydantic<2

if not hasattr(pydantic, "field_validator"):  # pragma: no cover - compatibility shim
    from pydantic import validator as _validator  # type: ignore

    def _compat_field_validator(*fields, mode=None, **kwargs):  # type: ignore
        if mode == "before":
            kwargs["pre"] = True
        return _validator(*fields, **kwargs)

    setattr(pydantic, "field_validator", _compat_field_validator)

import chromadb
from sentence_transformers import SentenceTransformer

from s2s.ingest import Document
from s2s.utils import chunk_text, ensure_dir, log_interaction


class RAGIndex:
    """Thin wrapper around Chroma for syllabus snippets."""

    def __init__(self, project: str, persist_root: Path = Path("data/processed/indices")) -> None:
        self.project = project
        self.persist_root = ensure_dir(persist_root)
        self.client = chromadb.PersistentClient(path=str(self.persist_root))
        self.collection = self.client.get_or_create_collection(
            name=self.project,
            metadata={"hnsw:space": "cosine"},
        )
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

    def ingest_documents(self, documents: Iterable[Document]) -> int:
        ids: List[str] = []
        texts: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for doc in documents:
            for idx, chunk in enumerate(chunk_text(doc.text)):
                chunk_id = f"{doc.id}-{idx}"
                ids.append(chunk_id)
                texts.append(chunk)
                metadatas.append({"doc_id": doc.id, "path": doc.path})
        if not ids:
            return 0

        embeddings = self.embedder.encode(texts, show_progress_bar=False).tolist()
        self.collection.upsert(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
        log_interaction(
            tag="rag_ingest",
            prompt=f"Ingested {len(ids)} chunks for project {self.project}",
            response="ok",
            metadata={"chunks": len(ids)},
        )
        return len(ids)

    def search(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        embeddings = self.embedder.encode([query], show_progress_bar=False).tolist()
        result = self.collection.query(query_embeddings=embeddings, n_results=k)
        hits: List[Dict[str, Any]] = []
        for ids, docs, metas, distances in zip(
            result["ids"], result["documents"], result["metadatas"], result["distances"]
        ):
            for idx in range(len(ids)):
                hits.append(
                    {
                        "id": ids[idx],
                        "text": docs[idx],
                        "metadata": metas[idx],
                        "distance": distances[idx],
                    }
                )
        log_interaction(
            tag="rag_search",
            prompt=query,
            response=f"{len(hits)} hits",
            metadata={"hits": hits[:2]},
        )
        return hits

    def count(self) -> int:
        return self.collection.count()

    def reset(self) -> None:
        ids = self.collection.get()["ids"]
        if ids:
            self.collection.delete(ids=ids)
