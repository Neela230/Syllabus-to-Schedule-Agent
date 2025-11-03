Name: Neela  
University: IIT Kanpur  
Department: Civil Engineering  

# Syllabus-to-Schedule (S2S) Agent

The S2S Agent ingests course syllabus and announcements, extracts graded work, plans milestone tasks, and exports a ready-to-use study schedule. It combines Retrieval-Augmented Generation (RAG), a LoRA-tuned extractor model, and a heuristic/LLM-backed planner to automate academic workflow management.

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
  

4. **Open UI (optional)**
   ```bash
   make ui
   ```

## System Requirements

- **Operating System**

1. Windows 10 / 11, Ubuntu 20.04 +, or macOS 12 +
2. Works on any OS supported by Python ≥ 3.9
   
- **Python Environment**  

   Python Version: ≥ 3.9 (recommended 3.10 – 3.11)

- **Network & API Access**

1. Internet connection required for installing dependencies and downloading pretrained models
2. No external API keys required by default (only if integrating optional external LLMs)

- **Optional Tools**

1. VS Code or PyCharm for IDE support
2. Git for cloning and version control

## Libraries Used

- **Core ML & NLP**

1. torch — PyTorch backend for model training/inference
2. transformers — for pretrained and LoRA-tuned extractor models
3. peft — parameter-efficient fine-tuning support
4. sentence-transformers — MiniLM embeddings for semantic indexing

- **Data Handling & Validation**

1. pandas — structured task data and CSV export
2. pydantic — schema validation and normalization
3. dateparser — natural-language date parsing

- **Parsing**

1. pdfplumber — PDF syllabus text extraction
2. beautifulsoup4 + lxml — HTML syllabus parsing

- **Retrieval & Storage**

1. chromadb — vector store for RAG (Retrieval-Augmented Generation)
2. sqlite3 — lightweight local schedule database

- **Interface & Logging**

1. typer — CLI interface
2. streamlit — web UI
3. loguru — clean logging
4. python-dotenv — environment variable management

- **Export & Output**

1. ics / icalendar — generate calendar files
2. csv / pandas — export schedules as CSV

- **Testing**

1. pytest — for unit and integration tests


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
