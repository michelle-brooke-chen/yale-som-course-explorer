"""Yale SOM Course Assistant Agent with Context."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from tools import search_courses, session_label

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUTPUT_DIR = ROOT / "output"
AUDIT_PATH = OUTPUT_DIR / "audit_trail.json"

load_dotenv(HERE / ".env")

OUTPUT_DIR.mkdir(exist_ok=True)

# In-memory follow-up context, kept separately for each user
_contexts: dict[Optional[int], dict] = {}


def _get_context(user_id: Optional[int]) -> dict:
    return _contexts.setdefault(user_id, {"last_search_results": [], "last_query": ""})


def run_agent(message: str, user_id: Optional[int] = None) -> dict:
    """Run the agent and return reply + tools used."""
    try:
        tools_used = []
        context = _get_context(user_id)

        # Pull out "Fall 1" / "Fall 2" before extracting other search terms
        session, remaining = _extract_session(message)
        search_query = _extract_search_terms(remaining)

        # Follow-up only when the message adds no new search criteria
        if (
            not search_query
            and not session
            and _is_follow_up_request(message)
            and context["last_search_results"]
        ):
            return _handle_follow_up(context)

        # Determine if this is a course-related question
        keywords = ["course", "class", "teach", "faculty", "schedule", "time", "category", "what", "find", "which", "show", "list", "fall"]
        is_course_question = any(kw.lower() in message.lower() for kw in keywords)

        if is_course_question and (search_query or session):
            search_result = search_courses(
                query=search_query or None,
                session=session,
            )
            tools_used.append("search_courses")

            # Store context for follow-ups
            context["last_search_results"] = search_result.results
            context["last_query"] = search_query

            if search_result.count > 0:
                courses = search_result.results
                reply = _generate_course_response(message, courses)
            else:
                criteria = " in ".join(
                    part for part in [search_query, session_label(session) if session else ""] if part
                )
                reply = f"No courses found matching '{criteria}'.\n\nTry searching by:\n• Faculty name (e.g., Kai Hao Yang)\n• Subject (e.g., Economics)\n• Session (e.g., Fall 1 or Fall 2)\n• Category (e.g., PhD)\n• Or a course number"
        else:
            reply = _generate_fallback_response(message)

        agent_result = {
            "reply": reply,
            "tools_used": tools_used,
        }

        _log_audit(message, agent_result)
        return agent_result

    except Exception as e:
        error_reply = f"Error: {str(e)}"
        agent_result = {
            "reply": error_reply,
            "tools_used": [],
        }
        _log_audit(message, agent_result, error=str(e))
        return agent_result


def _is_follow_up_request(message: str) -> bool:
    """Check if this is a follow-up to a previous search."""
    msg_lower = message.lower()
    follow_up_keywords = ["list", "them", "more", "detailed", "details", "tell", "about", "show", "display"]
    return any(kw in msg_lower for kw in follow_up_keywords)


def _handle_follow_up(context: dict) -> dict:
    """Handle follow-up questions about previous search results."""
    results = context["last_search_results"]

    if not results:
        return {
            "reply": "I don't have previous search results to show. Please search for courses first.",
            "tools_used": [],
        }

    # Deduplicate by title + number
    seen = {}
    unique_courses = []
    for course in results:
        key = (course.get("title"), course.get("number"))
        if key not in seen:
            seen[key] = course
            unique_courses.append(course)

    # Show details for unique courses (limit to 4 for readability)
    reply = f"Course details:\n"
    display_count = min(4, len(unique_courses))

    for i, course in enumerate(unique_courses[:display_count], 1):
        title = course.get("title", "Unknown")
        number = course.get("number", "N/A")
        faculty = course.get("faculty") or "Staff"
        category = course.get("category", "General")
        credits = course.get("credits", "N/A")
        desc = course.get("description", "")

        reply += f"\n{i}. {title} ({number})"
        reply += f"\n   Faculty: {faculty}"
        reply += f"\n   Session: {session_label(course.get('session', ''))}"
        reply += f"\n   Category: {category}"
        reply += f"\n   Credits: {credits}"
        if desc:
            reply += f"\n   {desc[:200]}..."

    if len(unique_courses) > display_count:
        reply += f"\n\nand {len(unique_courses) - display_count} more courses available"

    return {
        "reply": reply,
        "tools_used": ["search_courses"],
    }


def _extract_session(message: str) -> tuple[Optional[str], str]:
    """Detect a Fall 1 / Fall 2 / full-fall session and strip it from the message."""
    patterns = [
        (r"\bfall[\s\-]*(?:1|one|i)\b", "fall-1"),
        (r"\bfall[\s\-]*(?:2|two|ii)\b", "fall-2"),
        (r"\b(?:full[\s\-]*(?:fall|semester)|fall[\s\-]*semester)\b", "fall"),
    ]
    for pattern, session in patterns:
        if re.search(pattern, message, re.IGNORECASE):
            return session, re.sub(pattern, " ", message, flags=re.IGNORECASE)
    return None, message


def _extract_search_terms(message: str) -> str:
    """Extract key search terms from a natural language question."""
    remove_words = [
        "what", "is", "are", "show", "me", "tell", "teaching", "teach", "taught",
        "teaches", "courses", "course", "classes", "class", "by", "please", "can",
        "you", "do", "does", "find", "search", "professor", "prof", "dr", "list",
        "them", "more", "detailed", "details", "about", "display", "full",
        "which", "who", "when", "where", "the", "and", "for", "any", "there",
        "all", "available", "offered", "offer", "session", "term", "semester",
        "during", "give", "want", "know", "has", "have", "with", "that",
        "this", "those", "these", "his", "her", "their", "fall", "in", "on", "of",
    ]

    words = []
    for w in message.split():
        cleaned = re.sub(r"['’]s$", "", w.strip(".,?!;:()\"'"))
        if cleaned.lower() not in remove_words and len(cleaned) > 2:
            words.append(cleaned)

    return " ".join(words).strip()


def _generate_course_response(query: str, courses: list) -> str:
    """Generate a response based on found courses."""
    if not courses:
        return f"No courses found matching '{query}'."

    if len(courses) == 1:
        course = courses[0]
        return _format_single_course(course)

    # Deduplicate courses by title + number
    seen = {}
    unique_courses = []
    for course in courses:
        key = (course.get("title"), course.get("number"))
        if key not in seen:
            seen[key] = course
            unique_courses.append(course)

    # Show unique courses only
    reply = f"Found {len(unique_courses)} course(s):\n"

    for i, course in enumerate(unique_courses[:8], 1):
        title = course.get("title", "Unknown")
        number = course.get("number", "N/A")
        faculty = course.get("faculty") or "Staff"
        session = session_label(course.get("session", ""))

        reply += f"\n{i}. {title} ({number})"
        reply += f"\n   {faculty} · {session}"

    if len(unique_courses) > 8:
        reply += f"\n\nand {len(unique_courses) - 8} more courses"

    reply += "\n\nType 'more details' for full information."

    return reply


def _format_single_course(course: dict) -> str:
    """Format a single course for detailed display."""
    title = course.get("title", "Unknown")
    number = course.get("number", "N/A")
    faculty = course.get("faculty") or "Staff"
    time = course.get("time", "Time TBD")
    category = course.get("category", "General")
    credits = course.get("credits", "N/A")

    response = f"{title}\n({number})\n\n"
    response += f"Faculty: {faculty}\n"
    response += f"Session: {session_label(course.get('session', ''))}\n"
    response += f"Category: {category}\n"
    response += f"Credits: {credits}\n"
    response += f"Schedule: {time}"

    return response


def _generate_fallback_response(query: str) -> str:
    """Generate a helpful response when no courses match."""
    responses = {
        "hello": "Hi! I'm the Yale SOM course assistant. Ask me about:\n• Courses by faculty (e.g., 'What does Yang teach?')\n• Subject areas (e.g., 'Economics courses')\n• Categories (e.g., 'PhD courses')\n• Schedules (e.g., 'Monday courses')",
        "hi": "Hi! I'm the Yale SOM course assistant. Ask me about courses, faculty, schedules, or course content.",
        "help": "I can help you find Yale SOM courses. Try:\n• 'What strategy courses are available?'\n• 'Show me courses taught by Yang'\n• 'What courses meet on Monday?'",
        "thanks": "You're welcome! Let me know if you need help with anything else.",
        "thank you": "You're welcome! Feel free to ask about any courses.",
    }

    query_lower = query.lower().strip()
    for key, response in responses.items():
        if key in query_lower:
            return response

    return "I can help with questions about Yale SOM courses. Try asking about faculty members, course subjects, or schedules."


def _log_audit(message: str, result: dict, error: Optional[str] = None) -> None:
    """Append to audit trail."""
    try:
        if AUDIT_PATH.exists():
            audit_data = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        else:
            audit_data = []

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_message": message,
            "reply": result.get("reply", ""),
            "tools_used": result.get("tools_used", []),
        }
        if error:
            entry["error"] = error

        audit_data.append(entry)
        AUDIT_PATH.write_text(json.dumps(audit_data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"Failed to log audit: {e}")
