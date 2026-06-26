"""Result analyzer service (Phase 2).

Right now this only generates the empty CSV template a teacher fills in
after a paper has been printed. Upload + analyze functions will land here
as the rest of Phase 2 lands.
"""

import json
from typing import Optional

import pandas as pd

from app.repositories import papers_repository, questions_repository


def build_result_template_csv(paper_id: str) -> Optional[bytes]:
    """Returns a CSV template (header row only) for the given paper:

        roll_no, student_name, Q1 (marks: 2), Q2 (marks: 5), ...

    Question order matches paper.question_ids so the teacher's columns line
    up with the printed paper. Returns None if no paper with that id —
    caller maps that to 404.
    """
    paper = papers_repository.find_by_id(paper_id)
    if paper is None:
        return None

    question_ids = json.loads(paper["question_ids"])
    questions = []
    for qid in question_ids:
        q = questions_repository.find_by_id(qid)
        if q is not None:
            questions.append(q)

    columns = ["roll_no", "student_name"]
    for i, q in enumerate(questions, start=1):
        columns.append(f"Q{i} (marks: {q['marks']})")

    df = pd.DataFrame(columns=columns)
    return df.to_csv(index=False).encode("utf-8")
