# Deliverables Summary

This folder packages the artefacts required by **DS Internship Assignment.pptx.pdf** while referencing the full project in the repository root.

## Included Files

- `report.tex` – LaTeX final report consolidating architecture, training, evaluation, usage, and deliverable checklist.
- `prompts.txt` – Chronological list of user prompts from this collaboration.
- `../docs/architecture.md` – Detailed component architecture (referenced in the report).
- `../docs/ds_report.md` – Data science / fine-tuning report.
- `../logs/interactions.log` – JSONL log of all model/tool interactions (kept at repository level to avoid duplication).
- `../README.md` – Project quickstart with environment and usage instructions.

## How to Build the Report

```bash
cd deliverables
pdflatex report.tex  # run twice for ToC/refs if desired
```

## How to Run the Agent

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
make run             # ingest → index → extract → plan → export
make ui              # optional Streamlit preview
pytest               # regression tests
```

Outputs are written to `out/` (calendar, CSV, SQLite, JSON snapshots). Interaction logs live in `logs/interactions.log` and are ready for submission.

## Contact / Submission Notes

- Include repository URL and the contents of this `deliverables/` directory when submitting.
- Ensure `logs/interactions.log` accompanies the submission to satisfy the logging requirement.
- The prompts list in `prompts.txt` mirrors the conversation history for auditing.

Everything else remains unchanged in the project root to preserve functionality. Let me know if you need the LaTeX compiled to PDF or additional packaging. 
