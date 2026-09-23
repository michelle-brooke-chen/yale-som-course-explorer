"""Tools for the Yale SOM course assistant agent."""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel

from db import get_db


class SearchResult(BaseModel):
    """Result of a search operation."""
    count: int
    results: list[dict]


SESSION_LABELS = {
    "fall-1": "Fall 1",
    "fall-2": "Fall 2",
    "fall": "Full Fall semester",
}

# Columns a free-text query is matched against
QUERY_COLUMNS = [
    "course_title",
    "course_number",
    "course_description",
    "faculty_1",
    "course_category",
]


def session_label(session: str) -> str:
    """Human-readable label for a course_session value."""
    return SESSION_LABELS.get(session.lower().strip(), session or "TBD")


def _tokens(text: str) -> list[str]:
    """Lowercase words with punctuation and possessives stripped."""
    words = re.sub(r"['’]s\b", "", text.lower())
    return re.findall(r"[a-z0-9]+", words)


def all_words_clause(text: str, columns: list[str]) -> tuple[list[str], list[str]]:
    """SQL conditions requiring every word to appear in at least one column.

    Words can match in any order, so "Kai Hao Yang" finds "Yang, Kai Hao".
    Tokens are [a-z0-9] only, so they need no LIKE escaping.
    """
    clauses, params = [], []
    for word in _tokens(text):
        clauses.append("(" + " OR ".join(f"{col} LIKE ?" for col in columns) + ")")
        params.extend([f"%{word}%"] * len(columns))
    return clauses, params


def search_courses(
    query: Optional[str] = None,
    faculty: Optional[str] = None,
    category: Optional[str] = None,
    day: Optional[str] = None,
    session: Optional[str] = None,
) -> SearchResult:
    """Search Yale SOM courses in the courses table by various criteria."""
    max_results = 20
    clauses: list[str] = []
    params: list[str] = []

    if query:
        found, values = all_words_clause(query, QUERY_COLUMNS)
        clauses += found
        params += values

    if faculty:
        found, values = all_words_clause(faculty, ["faculty_1"])
        clauses += found
        params += values

    if session:
        clauses.append("lower(course_session) = ?")
        params.append(session.lower().strip())

    if category:
        clauses.append("course_category LIKE ?")
        params.append(f"%{category.strip()}%")

    if day:
        clauses.append("timings_day LIKE ?")
        params.append(f"%{day.strip()}%")

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    # One row per course (first section) so duplicate sections don't crowd out results
    sql = f"""
        SELECT MIN(id) AS id, course_title, course_number, faculty_1,
               course_category, timings_day, daytimes, course_description,
               faculty_bio, units, course_session, room
        FROM courses
        {where}
        GROUP BY course_title, course_number
        ORDER BY MIN(id)
        LIMIT ?
    """

    with get_db() as conn:
        rows = conn.execute(sql, [*params, max_results]).fetchall()

    normalized = [
        {
            "title": row["course_title"] or "",
            "number": row["course_number"] or "",
            "faculty": row["faculty_1"] or "",
            "category": row["course_category"] or "",
            "day": row["timings_day"] or "",
            "time": row["daytimes"] or "",
            "description": row["course_description"] or "",
            "faculty_bio": row["faculty_bio"] or "",
            "credits": row["units"] or "",
            "session": row["course_session"] or "",
            "room": row["room"] or "",
        }
        for row in rows
    ]

    return SearchResult(count=len(normalized), results=normalized)
