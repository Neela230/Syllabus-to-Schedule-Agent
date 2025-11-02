from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

import typer
from tabulate import tabulate

from s2s.ingest import Document
from s2s.ingest.pdf_reader import read_pdf
from s2s.ingest.html_reader import read_html_or_text
from s2s.rag import RAGIndex
from s2s.extract import AssignmentExtractor
from s2s.plan import TaskPlanner
from s2s.execute import schedule_tasks, write_calendar_ics, write_tasks_csv, write_sqlite
from s2s.schemas import AssignmentRecord, Task
from s2s.utils import ensure_dir, log_interaction, read_jsonl, write_jsonl

app = typer.Typer(help="Syllabus-to-Schedule Agent CLI.")


def _project_name(project: str | None) -> str:
    return project or os.getenv("S2S_PROJECT_NAME", "default")


def _data_dir() -> Path:
    return Path(os.getenv("S2S_DATA_DIR", "data"))


def _project_paths(project: str) -> Dict[str, Path]:
    base = _data_dir()
    processed = ensure_dir(base / "processed")
    out_dir = ensure_dir(Path("out"))
    return {
        "documents": processed / f"{project}_documents.jsonl",
        "assignments": out_dir / f"{project}_assignments.json",
        "plan": out_dir / f"{project}_plan.json",
        "ics": out_dir / "calendar.ics",
        "csv": out_dir / "tasks.csv",
        "sqlite": out_dir / "tasks.db",
    }


@app.command()
def ingest(path: Path, project: str = typer.Option(None, "--project", "-p")) -> None:
    """Ingest PDFs and HTML/txt files into normalized documents."""
    project = _project_name(project)
    docs: List[Document] = []
    for file_path in sorted(path.rglob("*")):
        if not file_path.is_file():
            continue
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            doc = read_pdf(file_path)
        elif suffix in {".html", ".htm", ".txt"}:
            doc = read_html_or_text(file_path)
        else:
            continue
        docs.append(doc)
    paths = _project_paths(project)
    write_jsonl(paths["documents"], [d.to_dict() for d in docs])
    log_interaction("cli_ingest", str(path), f"stored {len(docs)} documents", {"project": project})
    typer.echo(f"Ingested {len(docs)} documents for project '{project}'.")


@app.command()
def index(project: str = typer.Option(None, "--project", "-p")) -> None:
    """Index ingested documents into Chroma."""
    project = _project_name(project)
    paths = _project_paths(project)
    docs = [Document.from_dict(d) for d in read_jsonl(paths["documents"])]
    if not docs:
        raise typer.BadParameter("No documents found. Run ingest first.")
    rag_index = RAGIndex(project=project)
    chunks = rag_index.ingest_documents(docs)
    typer.echo(f"Indexed {chunks} chunks for project '{project}'.")


@app.command()
def extract(project: str = typer.Option(None, "--project", "-p")) -> None:
    """Run the extractor over indexed documents."""
    project = _project_name(project)
    paths = _project_paths(project)
    docs = [Document.from_dict(d) for d in read_jsonl(paths["documents"])]
    if not docs:
        raise typer.BadParameter("No documents found. Run ingest first.")
    extractor = AssignmentExtractor(force_rule_based=True)
    assignments: List[Dict[str, str]] = []
    for doc in docs:
        records = extractor.extract_many(doc.text, doc.path)
        for record in records:
            assignments.append(record.dict_for_storage())
    ensure_dir(paths["assignments"].parent)
    paths["assignments"].write_text(json.dumps(assignments, indent=2), encoding="utf-8")
    typer.echo(f"Extracted {len(assignments)} assignments for project '{project}'.")


@app.command()
def plan(project: str = typer.Option(None, "--project", "-p")) -> None:
    """Generate milestone plans for extracted assignments."""
    project = _project_name(project)
    paths = _project_paths(project)
    if not paths["assignments"].exists():
        raise typer.BadParameter("No assignment JSON found. Run extract first.")
    assignments = [AssignmentRecord(**item) for item in json.loads(paths["assignments"].read_text())]
    planner = TaskPlanner()
    plans: Dict[str, List[Dict[str, str]]] = {}
    for idx, record in enumerate(assignments):
        tasks = planner.plan(record)
        key = f"{record.assignment_title}::{Path(record.source_doc).name}::{idx}"
        plans[key] = [task.dict_for_storage() for task in tasks]
    paths["plan"].write_text(json.dumps(plans, indent=2), encoding="utf-8")
    typer.echo(f"Planned schedules for {len(plans)} assignments.")


@app.command()
def run(project: str = typer.Option(None, "--project", "-p")) -> None:
    """Run ingest->index->extract->plan->export pipeline."""
    project = _project_name(project)
    ingest(Path("data/raw"), project=project)
    index(project=project)
    extract(project=project)
    plan(project=project)
    _export_outputs(project)
    typer.echo("Pipeline completed.")


@app.command()
def show(project: str = typer.Option(None, "--project", "-p")) -> None:
    """Print summary of assignments and milestones."""
    project = _project_name(project)
    paths = _project_paths(project)
    if not paths["plan"].exists():
        raise typer.BadParameter("No plan available. Run plan first.")
    assignment_items = json.loads(paths["assignments"].read_text())
    assignments = {
        f'{item["assignment_title"]}::{Path(item["source_doc"]).name}::{idx}': item
        for idx, item in enumerate(assignment_items)
    }
    plans = json.loads(paths["plan"].read_text())
    table = []
    for title, tasks in plans.items():
        record = assignments.get(title)
        if not record:
            continue
        for task in tasks:
            table.append(
                [
                    record.get("course", ""),
                    record.get("assignment_title", ""),
                    task["title"],
                    task.get("earliest_start_iso", ""),
                    task["due_iso"],
                    task["hours_estimate"],
                ]
            )
    typer.echo(tabulate(table, headers=["Course", "Assignment", "Task", "Start", "Due", "Hours"]))


@app.command()
def eval(project: str = typer.Option(None, "--project", "-p")) -> None:
    """Run evaluation script."""
    subprocess.run(["python", "training/eval_extraction.py"], check=True)


def _export_outputs(project: str) -> None:
    paths = _project_paths(project)
    assignment_items = json.loads(paths["assignments"].read_text())
    assignments = [AssignmentRecord(**item) for item in assignment_items]
    plans_data = json.loads(paths["plan"].read_text())
    paired: List[Tuple[AssignmentRecord, List[Task]]] = []
    for idx, assignment in enumerate(assignments):
        key = f"{assignment.assignment_title}::{Path(assignment.source_doc).name}::{idx}"
        tasks = [Task(**task) for task in plans_data.get(key, [])]
        paired.append((assignment, tasks))
    write_calendar_ics(paired, output_dir=paths["ics"].parent, filename=paths["ics"].name)
    write_tasks_csv(paired, output_dir=paths["csv"].parent, filename=paths["csv"].name)
    write_sqlite(paired, output_path=paths["sqlite"])


if __name__ == "__main__":
    app()
