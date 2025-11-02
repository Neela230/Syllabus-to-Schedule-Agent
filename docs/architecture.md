# Architecture Overview

## Component Diagram

```
Ingest (pdf_reader, html_reader)
    ↓ documents.jsonl
RAG Index (Chroma + MiniLM)
    ↘ retrieval for planner
Extractor (LoRA T5) → Validate (Pydantic)
    ↓ assignments.json
Planner (heuristic + optional LLM)
    ↓ plan.json
Scheduler → Exporters (ICS/CSV/SQLite)
```

## Processing Flow

1. **Ingest**: PDF/HTML parsers emit `Document` objects. Stored in `data/processed/<project>_documents.jsonl`.
2. **Index**: Chroma persistent collection with MiniLM embeddings for self-check retrieval.
3. **Extract**: LoRA-adapted `t5-small` converts text into `AssignmentRecord` JSON. Rule-based fallback keeps tests lightweight.
4. **Validate**: Pydantic + dateparser normalize fields and enforce schema.
5. **Plan**: TaskPlanner estimates effort, optionally refines with an LLM pipeline, and generates 2–5 milestone `Task`s.
6. **Execute**: Backward scheduling ensures tasks finish before due date. Exports feed ICS calendar events, CSV, and SQLite tables.
7. **Logging**: Every LLM-like interaction (extraction, planning) appends JSONL logs to `logs/interactions.log`.

## Model Choices

- **Retriever**: `sentence-transformers/all-MiniLM-L6-v2` balances speed and accuracy for short academic passages.
- **Extractor**: Small `t5-small` fine-tuned via PEFT LoRA for efficient deployment under limited compute.
- **Planner**: Deterministic heuristic planning with optional text2text model for richer plans, keeping offline behavior predictable.

## Agent Pattern Alignment

- **Reason**: Extraction model interprets structure; planner estimates schedule.
- **Plan**: TaskPlanner builds DAG of milestones with dependencies.
- **Execute**: Scheduler/exporters produce actionable artifacts (ICS, CSV, DB).
- **Self-monitor**: Logs + evaluation metrics (field EM, micro-F1, date accuracy) enable iteration.
