import json
from pathlib import Path

import streamlit as st

from s2s.schemas import AssignmentRecord, Task
from s2s.execute import write_calendar_ics, write_tasks_csv, write_sqlite


def load_assignments(project: str) -> list[AssignmentRecord]:
    path = Path("out") / f"{project}_assignments.json"
    if not path.exists():
        return []
    return [AssignmentRecord(**item) for item in json.loads(path.read_text())]


def load_plan(project: str) -> dict[str, list[Task]]:
    path = Path("out") / f"{project}_plan.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text())
    return {title: [Task(**task) for task in tasks] for title, tasks in raw.items()}


def main() -> None:
    st.title("Syllabus-to-Schedule Agent")
    project = st.sidebar.text_input("Project", value="default")
    assignments = load_assignments(project)
    plans = load_plan(project)

    if not assignments:
        st.warning("No assignments found. Run the CLI pipeline first.")
        return

    for record in assignments:
        st.subheader(record.assignment_title)
        st.markdown(f"**Course:** {record.course or 'Unknown'}")
        st.markdown(f"**Due:** {record.due_datetime_iso}")
        st.json(record.dict_for_storage())

        tasks = plans.get(record.assignment_title, [])
        if tasks:
            st.write("Milestones")
            for task in tasks:
                st.markdown(
                    f"- {task.title} ({task.hours_estimate}h) {task.earliest_start_iso} -> {task.due_iso}"
                )

    if st.button("Export ICS/CSV/SQLite"):
        paired = [(record, plans.get(record.assignment_title, [])) for record in assignments]
        write_calendar_ics(paired)
        write_tasks_csv(paired)
        write_sqlite(paired)
        st.success("Exports written to out/ directory.")


if __name__ == "__main__":
    main()
