"""Create the tables in Postgres (Supabase) and load the data.

- courses: loaded from data/yale_som_classes.json when the table is empty
- users and chats: copied from the old SQLite file (data/yale_som.db) if it exists

Safe to re-run; rows that are already there are skipped.

Run from backend/:  python seed_database.py
"""

from __future__ import annotations

import json
import sqlite3

from psycopg.types.json import Jsonb

from db import ROOT, get_db, init_db

JSON_PATH = ROOT / "data" / "yale_som_classes.json"
SQLITE_PATH = ROOT / "data" / "yale_som.db"

# courses column -> key in the JSON file
COURSE_FIELDS = {
    "course_id": "Course ID",
    "course_number": "Course Number",
    "course_title": "Course Title",
    "course_category": "Course Category",
    "course_type": "Course Type",
    "course_session": "Course Session",
    "course_description": "Course Description",
    "faculty_1": "Faculty 1",
    "faculty_1_email": "Faculty 1 Email",
    "faculty_bio": "faculty_bio",
    "daytimes": "Daytimes",
    "timings_day": "Timings Day",
    "timings_start": "Timings StartTime",
    "timings_end": "Timings EndTime",
    "room": "Room",
    "section": "Section",
    "units": "Units",
    "term_code": "TermCode",
    "syllabus": "Syllabus",
    "old_syllabus": "Old Syllabus",
    "session_start_date": "Course Session Start date",
    "session_end_date": "Course Session End Date",
    "bid_or_permission": "Bid Or Permission",
}
DATE_COLUMNS = {"session_start_date", "session_end_date"}


def iso_date(value: str) -> str | None:
    """Convert '20260902 000000.000' to '2026-09-02'."""
    digits = (value or "")[:8]
    if len(digits) != 8 or not digits.isdigit():
        return None
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"


def course_values(course: dict) -> list:
    values = []
    for column, key in COURSE_FIELDS.items():
        value = (course.get(key) or "").strip()
        values.append(iso_date(value) if column in DATE_COLUMNS else value)
    return values


def reset_id_sequence(conn, table: str) -> None:
    """Point the id counter past copied rows so new rows don't collide."""
    conn.execute(
        f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
        f"COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM {table}"
    )


def seed_courses(conn) -> int:
    if conn.execute("SELECT COUNT(*) AS n FROM courses").fetchone()["n"]:
        return 0

    courses = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    columns = ", ".join(["id", *COURSE_FIELDS])
    placeholders = ", ".join(["%s"] * (len(COURSE_FIELDS) + 1))
    with conn.cursor() as cur:
        cur.executemany(
            f"INSERT INTO courses ({columns}) VALUES ({placeholders})",
            [[i, *course_values(c)] for i, c in enumerate(courses, start=1)],
        )
    reset_id_sequence(conn, "courses")
    return len(courses)


def copy_accounts_and_chats(conn) -> tuple[int, int]:
    if not SQLITE_PATH.exists():
        return 0, 0

    source = sqlite3.connect(SQLITE_PATH)
    source.row_factory = sqlite3.Row
    tables = {r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    users = source.execute("SELECT * FROM users").fetchall() if "users" in tables else []
    chats = source.execute("SELECT * FROM chats").fetchall() if "chats" in tables else []
    source.close()

    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO users (id, username, password_hash, created_at) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
            [(u["id"], u["username"], u["password_hash"], f"{u['created_at']}+00") for u in users],
        )
        users_added = max(cur.rowcount, 0) if users else 0
        cur.executemany(
            "INSERT INTO chats (id, user_id, user_message, reply, tools_used, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            [
                (
                    c["id"],
                    c["user_id"],
                    c["user_message"],
                    c["reply"],
                    Jsonb(json.loads(c["tools_used"])),
                    f"{c['created_at']}+00",
                )
                for c in chats
            ],
        )
        chats_added = max(cur.rowcount, 0) if chats else 0
    reset_id_sequence(conn, "users")
    reset_id_sequence(conn, "chats")
    return users_added, chats_added


def main() -> None:
    init_db()
    with get_db() as conn:
        added = seed_courses(conn)
        users, chats = copy_accounts_and_chats(conn)
        totals = {
            table: conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
            for table in ("courses", "users", "chats")
        }

    print(f"Loaded {added} courses; copied {users} users and {chats} chats from SQLite.")
    print(f"Totals now: {totals}")


if __name__ == "__main__":
    main()
