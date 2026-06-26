"""
Syllabus CSV ko database mein import karne wala script.

Usage:
    python import_syllabus.py syllabus_topics_unit1_sample.csv --subject Mathematics --grade "Grade 1"

Aap apni khud ki books ke liye bhi CSV bana ke isi script se import kar sakte
hain — bas wahi columns hone chahiye: unit_no,unit_title,page_range,
subtopic_title,activity_type,page_no,learning_outcome_snippet
"""

import argparse

from app.core.database import init_db
from app.services import syllabus_service

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import syllabus CSV into the question-bank database"
    )
    parser.add_argument("csv_path", help="Path to the syllabus CSV file")
    parser.add_argument("--subject", required=True, help="e.g. Mathematics")
    parser.add_argument("--grade", default="", help="e.g. Grade 1")
    args = parser.parse_args()

    init_db()
    count = syllabus_service.import_from_csv(args.csv_path, args.subject, args.grade)
    print(
        f"{count} syllabus topics imported for {args.subject} ({args.grade or 'no grade specified'})."
    )
