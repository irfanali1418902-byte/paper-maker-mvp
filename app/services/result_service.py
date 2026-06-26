"""Result analyzer service (Phase 2).

Two responsibilities so far:
  - build_result_template_csv: empty CSV for the teacher to fill in
  - import_results: validate the filled-in CSV/xlsx and persist it

Analysis (per-student totals, per-question pass rate, per-bloom
breakdown) will land here as the rest of Phase 2 lands.
"""

import io
import json
import uuid
from typing import Optional

import pandas as pd

from app.repositories import papers_repository, questions_repository, result_repository
from app.services.exceptions import ResultsValidationError


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


def _parse_uploaded_file(filename: str, file_bytes: bytes) -> pd.DataFrame:
    """Picks the right pandas reader by extension. Bad/unsupported files
    raise ValueError so the route can return 400 instead of leaking a
    pandas traceback."""
    lower = filename.lower()
    try:
        if lower.endswith(".csv"):
            return pd.read_csv(io.BytesIO(file_bytes))
        if lower.endswith(".xlsx") or lower.endswith(".xls"):
            return pd.read_excel(io.BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"File parse fail hui: {e}") from e
    raise ValueError(f"Unsupported file type for '{filename}'. Use .csv or .xlsx.")


def import_results(paper_id: str, filename: str, file_bytes: bytes) -> Optional[dict]:
    """Validates the uploaded results file and saves it.

    Returns:
        {"upload_id": str, "rows_saved": int}  -- per-cell rows inserted

    Returns None if the paper doesn't exist (route maps to 404). Raises
    ResultsValidationError if the file has any structural or content
    issue (route maps to 400 with the full errors list). Raises
    ValueError on unparseable/wrong-type files.
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

    df = _parse_uploaded_file(filename, file_bytes)

    # Structural checks first — if the shape is wrong, per-row checks are
    # meaningless. Report and bail.
    expected_col_count = 2 + len(questions)
    if len(df.columns) != expected_col_count:
        raise ResultsValidationError(
            [
                {
                    "row": 1,
                    "issue": (
                        f"Column count mismatch: expected {expected_col_count} columns "
                        f"(roll_no, student_name, then {len(questions)} question columns), "
                        f"got {len(df.columns)}."
                    ),
                }
            ]
        )
    if df.columns[0] != "roll_no" or df.columns[1] != "student_name":
        raise ResultsValidationError(
            [
                {
                    "row": 1,
                    "issue": "First two columns must be 'roll_no' and 'student_name'.",
                }
            ]
        )

    # Per-row validation. Collect every error so the teacher can fix the
    # whole sheet in one pass instead of upload-edit-upload looping.
    errors: list[dict] = []
    for pandas_idx, row in df.iterrows():
        # +2 so the row number matches what the teacher sees in their
        # spreadsheet (header is row 1, first data row is row 2).
        spreadsheet_row = int(pandas_idx) + 2

        roll_no = row["roll_no"]
        if pd.isna(roll_no) or str(roll_no).strip() == "":
            errors.append({"row": spreadsheet_row, "issue": "roll_no is missing."})

        student_name = row["student_name"]
        if pd.isna(student_name) or str(student_name).strip() == "":
            errors.append({"row": spreadsheet_row, "issue": "student_name is missing."})

        for q_idx, question in enumerate(questions):
            col_name = df.columns[2 + q_idx]
            value = row[col_name]

            if pd.isna(value):
                errors.append({"row": spreadsheet_row, "issue": f"Q{q_idx + 1} marks missing."})
                continue

            try:
                float_value = float(value)
            except (ValueError, TypeError):
                errors.append(
                    {
                        "row": spreadsheet_row,
                        "issue": f"Q{q_idx + 1} marks must be a number, got '{value}'.",
                    }
                )
                continue

            if not float_value.is_integer():
                errors.append(
                    {
                        "row": spreadsheet_row,
                        "issue": f"Q{q_idx + 1} marks must be a whole number, got {value}.",
                    }
                )
                continue

            marks = int(float_value)
            if marks < 0:
                errors.append(
                    {
                        "row": spreadsheet_row,
                        "issue": f"Q{q_idx + 1} marks ({marks}) cannot be negative.",
                    }
                )
                continue

            max_marks = question["marks"]
            if marks > max_marks:
                errors.append(
                    {
                        "row": spreadsheet_row,
                        "issue": f"Q{q_idx + 1} marks ({marks}) exceed max ({max_marks}).",
                    }
                )

    if errors:
        raise ResultsValidationError(errors)

    # All-or-nothing semantics: don't write anything unless every row passed.
    upload_id = str(uuid.uuid4())
    result_repository.insert_upload(upload_id=upload_id, paper_id=paper_id, filename=filename)

    rows_saved = 0
    for _, row in df.iterrows():
        for q_idx, question in enumerate(questions):
            col_name = df.columns[2 + q_idx]
            marks = int(float(row[col_name]))
            result_repository.insert_student_result(
                result_id=str(uuid.uuid4()),
                result_upload_id=upload_id,
                roll_no=str(row["roll_no"]).strip(),
                student_name=str(row["student_name"]).strip(),
                question_id=question["id"],
                marks_obtained=marks,
            )
            rows_saved += 1

    return {"upload_id": upload_id, "rows_saved": rows_saved}
