"""
Seed a paper with an engineered large class so the Phase B Difficulty Index
(P-value) and Discrimination Index (D) flags can be demonstrated.

The Discrimination Index only becomes reliable at >=10 students, so the small
real uploads can't show its flags. This script uploads a class whose marks are
deliberately shaped so each flag category appears — most importantly a
mis-keyed question (weak students get it, strong students miss it) that
produces a negative D and the "check your answer key" flag.

Usage:
    python seed_large_class.py <paper_id> [--students 12]

It reads the paper's real per-question max marks via the service layer and
imports through result_service — no raw SQL, same layering as the app.
"""

import argparse
import csv
import io

from app.core.database import init_db
from app.services import paper_service, result_service

# A paper needs at least this many questions for the script to place its
# special items (too_easy / poor / too_hard / mis-key) and still have anchor
# questions left to drive a clean ability ordering.
MIN_QUESTIONS = 5

# Below this many students the top/bottom split — and therefore D — is not
# statistically reliable (matches item_analysis_service.MIN_STUDENTS_FOR_RELIABLE_D).
RELIABLE_D_STUDENTS = 10


def _block_for(index: int, total: int) -> str:
    """Split students into high / mid / low ability terciles by index."""
    if index < total / 3:
        return "H"
    if index < 2 * total / 3:
        return "M"
    return "L"


def _marks_for(block: str, q_index: int, max_marks: int) -> int:
    """Engineered marks for one (student block, question) cell. The first four
    questions are the flagged scenarios; the rest are ability-tracking anchors
    that establish the total-score ordering."""
    high, mid = block == "H", block == "M"
    half = max_marks // 2 if max_marks >= 2 else 1

    if q_index == 0:  # too_easy: everyone full marks
        return max_marks
    if q_index == 1:  # poor discrimination: flat ~half for everyone
        return half
    if q_index == 2:  # too_hard: only top ability scrapes a single mark
        return 0
    if q_index == 3:  # mis-keyed: low block aces it, high block misses -> D<0
        return 0 if high else (min(1, max_marks) if mid else max_marks)
    # anchors: track ability so the total ordering is unambiguous
    return max_marks if high else (half if mid else 0)


def build_csv(questions: list[dict], student_count: int) -> bytes:
    """Build the results CSV (header + one row per student) as UTF-8 bytes,
    matching the upload template's column shape."""
    header = ["roll_no", "student_name"]
    header += [f"Q{i + 1} (marks: {q['marks']})" for i, q in enumerate(questions)]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    for i in range(student_count):
        block = _block_for(i, student_count)
        marks = [_marks_for(block, qi, q["marks"]) for qi, q in enumerate(questions)]
        writer.writerow([f"R{i + 1:03d}", f"Student {block}{i + 1}"] + marks)
    return buf.getvalue().encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a paper with an engineered large class")
    parser.add_argument("paper_id", help="Existing paper id to attach the results upload to")
    parser.add_argument("--students", type=int, default=12, help="Class size (default 12)")
    args = parser.parse_args()

    init_db()

    paper = paper_service.get_paper_with_questions(args.paper_id)
    if paper is None:
        raise SystemExit(f"Paper '{args.paper_id}' nahi mila.")
    questions = paper["questions"]
    if len(questions) < MIN_QUESTIONS:
        raise SystemExit(
            f"Paper mein sirf {len(questions)} questions hain; kam se kam "
            f"{MIN_QUESTIONS} chahiye taake flag scenarios ban sakein."
        )

    csv_bytes = build_csv(questions, args.students)
    result = result_service.import_results(args.paper_id, "seed_large_class.csv", csv_bytes)

    print(
        f"Uploaded {args.students}-student class — upload_id={result['upload_id']}, "
        f"rows_saved={result['rows_saved']}."
    )
    if args.students < RELIABLE_D_STUDENTS:
        print(
            f"Note: {args.students} students < {RELIABLE_D_STUDENTS}, D-index reliable nahi hoga."
        )
    print(
        "Expected flags: Q1 too_easy, Q2 poor-discrimination, Q3 too_hard, "
        "Q4 problematic (mis-key, D<0)."
    )


if __name__ == "__main__":
    main()
