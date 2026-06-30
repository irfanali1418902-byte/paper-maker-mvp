"""Quick stats for the home screen — read-only aggregates across tables.

Each count comes from its own single-table repository; this service just
stitches them together. The 'this month' boundary is computed in UTC to match
SQLite's CURRENT_TIMESTAMP (which stores uploaded_at in UTC).
"""

from datetime import datetime, timezone

from app.repositories import papers_repository, questions_repository, result_repository


def get_quick_stats() -> dict:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return {
        "total_papers": papers_repository.count_all(),
        "uploads_this_month": result_repository.count_uploads_since(
            month_start.strftime("%Y-%m-%d %H:%M:%S")
        ),
        "top_subject": papers_repository.top_subject(),
        "total_questions": questions_repository.count_all(),
    }
