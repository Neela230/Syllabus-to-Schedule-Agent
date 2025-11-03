# Deliverables Summary

This folder packages the artefacts required by **DS Internship Assignment.pptx.pdf** while referencing the full project in the repository root.

## Included Files

- `report.tex` – LaTeX final report consolidating architecture, training, evaluation, usage, requirement coverage.
- `prompts.txt` – Chronological list of user prompts from this collaboration.
- `../docs/architecture.md` – Detailed component architecture.
- `../docs/ds_report.md` – Data science / fine-tuning report.
- `../logs/interactions.log` – JSONL log of all model/tool interactions.
- `../README.md` – Project quickstart with environment and usage instructions.

## Build the Report

```bash
cd deliverables
pdflatex report.tex
```

## Run the Agent

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
make run
make ui
pytest
```

Outputs are written to `out/` (ICS, CSV, JSON, SQLite). Interaction logs live in `logs/interactions.log` for submission.

## Submission Notes

- Provide the repository URL and this `deliverables/` directory when submitting.
- Ensure `logs/interactions.log` accompanies the submission.
- The prompts list in `prompts.txt` mirrors the conversation history for auditing.
