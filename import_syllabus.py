"""
Syllabus CSV ko database mein import karne wala script.

Usage:
    python import_syllabus.py syllabus_topics_unit1_sample.csv --subject Mathematics --grade "Grade 1"

Aap apni khud ki books ke liye bhi CSV bana ke isi script se import kar sakte
hain — bas wahi columns hone chahiye: unit_no,unit_title,page_range,
subtopic_title,activity_type,page_no,learning_outcome_snippet
"""
import argparse
import csv
import uuid

from database import init_db, get_connection


def import_csv(csv_path: str, subject: str, grade: str) -> int:
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    inserted = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            topic_id = str(uuid.uuid4())
            try:
                cur.execute(
                    """INSERT INTO syllabus_topics
                       (id, subject, grade, unit_no, unit_title, page_range,
                        subtopic_title, activity_type, page_no, learning_outcome)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        topic_id,
                        subject,
                        grade,
                        int(row["unit_no"]),
                        row["unit_title"],
                        row["page_range"],
                        row["subtopic_title"],
                        row["activity_type"],
                        int(row["page_no"]) if row["page_no"] else None,
                        row.get("learning_outcome_snippet", ""),
                    ),
                )
                inserted += 1
            except Exception as e:
                # Duplicate (UNIQUE constraint) ya koi aur row-level issue -- skip kar ke aage badho
                print(f"Skipped row (subtopic: {row.get('subtopic_title')}): {e}")

    conn.commit()
    conn.close()
    return inserted


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import syllabus CSV into the question-bank database")
    parser.add_argument("csv_path", help="Path to the syllabus CSV file")
    parser.add_argument("--subject", required=True, help="e.g. Mathematics")
    parser.add_argument("--grade", default="", help="e.g. Grade 1")
    args = parser.parse_args()

    count = import_csv(args.csv_path, args.subject, args.grade)
    print(f"{count} syllabus topics imported for {args.subject} ({args.grade or 'no grade specified'}).")
