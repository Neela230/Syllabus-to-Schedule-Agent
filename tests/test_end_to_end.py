from pathlib import Path

from s2s.ingest import Document
from s2s.rag import RAGIndex
from s2s.extract import AssignmentExtractor
from s2s.plan import TaskPlanner
from s2s.execute import schedule_tasks, write_calendar_ics, write_tasks_csv
from s2s.schemas import AssignmentRecord


def test_pipeline_tmpdir(tmp_path: Path):
    doc = Document(
        id="doc1",
        path="sample.txt",
        text="Course: Pipelines\nAssignment: Integration Test\nDue: May 5 2024 21:00\nSubmit: Code tarball",
        pages=["Course: Pipelines ..."],
    )
    rag = RAGIndex(project="pytest", persist_root=tmp_path / "index")
    rag.reset()
    rag.ingest_documents([doc])

    extractor = AssignmentExtractor(force_rule_based=True)
    record = extractor.extract(doc.text, doc.path)
    planner = TaskPlanner()
    tasks = planner.plan(record)
    scheduled = schedule_tasks(record, tasks)

    out_dir = tmp_path / "out"
    write_calendar_ics([(record, scheduled)], output_dir=out_dir)
    write_tasks_csv([(record, scheduled)], output_dir=out_dir)

    assert (out_dir / "calendar.ics").exists()
    assert (out_dir / "tasks.csv").exists()
    assert isinstance(record, AssignmentRecord)
