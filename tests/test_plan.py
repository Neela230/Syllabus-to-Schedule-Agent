from s2s.schemas import AssignmentRecord
from s2s.plan import TaskPlanner


def build_record() -> AssignmentRecord:
    return AssignmentRecord(
        course="Planning 101",
        assignment_title="Milestone Essay",
        due_datetime_iso="2024-04-01T17:00:00",
        deliverables=["Essay draft"],
        points_or_weight="15%",
        source_doc="test",
        evidence_spans=["Due April 1 5 PM"],
        confidence=0.8,
    )


def test_planner_generates_tasks():
    planner = TaskPlanner()
    tasks = planner.plan(build_record())
    assert 2 <= len(tasks) <= 5
    assert sum(task.hours_estimate for task in tasks) >= 2
    for task in tasks:
        assert task.due_iso
    titles = [task.title for task in tasks]
    assert len(set(titles)) == len(titles)
    for task in tasks[1:]:
        assert task.depends_on
