Name: Neela  
University: IIT Kanpur  
Department: Civil Engineering  

# Syllabus-to-Schedule (S2S) Agent

The S2S Agent ingests course syllabi and announcements, extracts graded work, plans milestone tasks, and exports a ready-to-use study schedule. It combines Retrieval-Augmented Generation (RAG), a LoRA-tuned extractor model, and a heuristic/LLM-backed planner to automate academic workflow management.

## Quickstart

1. **Create environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   make setup
   ```

2. **Run end-to-end on sample data**
   ```bash
   make run
   ```

3. **Inspect outputs**
   - `out/calendar.ics` – import into Google Calendar (“Settings & Import” → “Import”).
   - `out/tasks.csv` – task table for spreadsheets or PM tools.


## Project Overview

- **Ingest**: Parse PDF, HTML, and text syllabi into normalized documents.
- **Index**: Build a Chroma semantic index with MiniLM embeddings.
- **Extract**: Apply a LoRA-adapted `t5-small` to generate structured assignment JSON.
- **Validate**: Clean and normalize fields with Pydantic + dateparser.
- **Plan**: Produce milestone tasks with dependencies and duration estimates.
- **Execute**: Backward-schedule milestones and export ICS/CSV/SQLite.
- **Evaluate**: Field EM, micro-F1, date accuracy, and end-to-end schedule checks.

## Repository Map

See `docs/architecture.md` for a deep dive and `docs/ds_report.md` for the ML workflow.
