"""One-time migration: add session dates and enrollment type to the courses table.

Copies them from data/yale_som_classes.json, matched by course_id. Safe to re-run.

Run from backend/:  python migrate_course_details.py
"""

from __future__ import annotations

import json

from db import DB_PATH, ROOT, get_db

JSON_PATH = ROOT / "data" / "yale_som_classes.json"

NEW_COLUMNS = ["session_start_date", "session_end_date", "bid_or_permission"]


def iso_date(value: str) -> str | None:
    """Convert '20260902 000000.000' to '2026-09-02'."""
    digits = (value or "")[:8]
    if len(digits) != 8 or not digits.isdigit():
        return None
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"


def main() -> None:
    courses = json.loads(JSON_PATH.read_text(encoding="utf-8"))

    with get_db() as conn:
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(courses)")}
        for column in NEW_COLUMNS:
            if column not in existing:
                conn.execute(f"ALTER TABLE courses ADD COLUMN {column} TEXT")

        updated = 0
        for c in courses:
            cursor = conn.execute(
                """
                UPDATE courses
                SET session_start_date = ?, session_end_date = ?, bid_or_permission = ?
                WHERE course_id = ?
                """,
                (
                    iso_date(c.get("Course Session Start date", "")),
                    iso_date(c.get("Course Session End Date", "")),
                    c.get("Bid Or Permission") or None,
                    c.get("Course ID"),
                ),
            )
            updated += cursor.rowcount

        missing = conn.execute(
            "SELECT COUNT(*) FROM courses WHERE session_start_date IS NULL"
        ).fetchone()[0]

    print(f"Updated {updated} courses in {DB_PATH.name}; {missing} still without dates.")


if __name__ == "__main__":
    main()
