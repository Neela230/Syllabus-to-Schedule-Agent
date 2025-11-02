from s2s.extract import AssignmentExtractor
from s2s.schemas import AssignmentRecord


def test_rule_based_extractor_basic():
    text = (
        "Course: Intro to Testing\n"
        "Assignment: Unit Test Draft\n"
        "Due: March 10 2024 at 11:59 PM\n"
        "Submit: PDF write-up"
    )
    extractor = AssignmentExtractor(force_rule_based=True)
    record = extractor.extract(text, "test_doc")
    assert isinstance(record, AssignmentRecord)
    assert record.assignment_title == "Unit Test Draft"
    assert record.deliverables
    assert record.due_datetime_iso.startswith("2024-03-10")


def test_assignment_confidence_bounds():
    text = "Assignment: Placeholder\nDue: April 1 2024 09:00"
    extractor = AssignmentExtractor(force_rule_based=True)
    record = extractor.extract(text, "test_doc")
    assert 0.0 <= record.confidence <= 1.0
