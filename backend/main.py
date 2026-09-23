"""Yale SOM course explorer API desk.

Run from backend/:  uvicorn main:app --reload --port 8000
Open API docs:      http://127.0.0.1:8000/docs
Frontend (Vite):    http://127.0.0.1:5173
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from agent import run_agent
from auth import (
    create_token,
    get_current_user,
    hash_password,
    validate_credentials,
    verify_password,
)
from db import get_db, init_db
from tools import QUERY_COLUMNS, all_words_clause

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")

init_db()

# Sites allowed to call the API from a browser, e.g. the Render static site URL
ALLOWED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

app = FastAPI(title="Yale SOM Courses", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    reply: str
    tools_used: list[str] = Field(default_factory=list)


class Credentials(BaseModel):
    username: str
    password: str


class User(BaseModel):
    id: int
    username: str


class AuthResponse(BaseModel):
    token: str
    user: User


class SavedChat(BaseModel):
    id: int
    user_message: str
    reply: str
    tools_used: list[str]
    created_at: str


class ChatHistoryResponse(BaseModel):
    chats: list[SavedChat]


@app.get("/api/health")
def health():
    return {"ok": True, "database": "postgres"}


def normalize_course(row: dict) -> dict:
    """Shape a courses-table row the way the frontend expects."""
    return {
        "id": row["course_id"] or "",
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
        "start_date": row["session_start_date"] or "",
        "end_date": row["session_end_date"] or "",
        "enrollment": row["bid_or_permission"] or "",
        "faculty_email": (row["faculty_1_email"] or "").strip(),
        "syllabus": row["syllabus"] or row["old_syllabus"] or "",
    }


@app.get("/api/courses")
def list_courses(q: str | None = Query(default=None)):
    """Return courses for the React catalog (optional text filter)."""
    clauses, params = all_words_clause(q or "", QUERY_COLUMNS)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with get_db() as conn:
        rows = conn.execute(f"SELECT * FROM courses {where} ORDER BY id", params).fetchall()

    normalized = [normalize_course(row) for row in rows]
    return {"count": len(normalized), "courses": normalized}


@app.post("/api/auth/register", response_model=AuthResponse, status_code=201)
def register(body: Credentials):
    username = body.username.strip()
    error = validate_credentials(username, body.password)
    if error:
        raise HTTPException(status_code=400, detail=error)

    try:
        with get_db() as conn:
            row = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
                (username, hash_password(body.password)),
            ).fetchone()
            user_id = row["id"]
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="That username is already taken.")

    return AuthResponse(token=create_token(user_id), user=User(id=user_id, username=username))


@app.post("/api/auth/login", response_model=AuthResponse)
def login(body: Credentials):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE lower(username) = lower(%s)",
            (body.username.strip(),),
        ).fetchone()

    if not verify_password(body.password, row["password_hash"] if row else None):
        raise HTTPException(status_code=401, detail="Incorrect username or password.")

    return AuthResponse(
        token=create_token(row["id"]),
        user=User(id=row["id"], username=row["username"]),
    )


@app.get("/api/auth/me", response_model=User)
def me(user: dict = Depends(get_current_user)):
    return User(**user)


@app.get("/api/chats", response_model=ChatHistoryResponse)
def chat_history(user: dict = Depends(get_current_user)):
    """The signed-in user's saved chat messages, oldest first."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, user_message, reply, tools_used, created_at
            FROM chats
            WHERE user_id = %s
            ORDER BY id
            """,
            (user["id"],),
        ).fetchall()

    return ChatHistoryResponse(chats=[
        SavedChat(
            id=row["id"],
            user_message=row["user_message"],
            reply=row["reply"],
            tools_used=row["tools_used"],
            created_at=row["created_at"].isoformat(),
        )
        for row in rows
    ])


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest, user: dict = Depends(get_current_user)):
    result = run_agent(body.message, user_id=user["id"])
    reply = result.get("reply", "")
    tools_used = list(result.get("tools_used") or [])

    with get_db() as conn:
        conn.execute(
            "INSERT INTO chats (user_id, user_message, reply, tools_used) VALUES (%s, %s, %s, %s)",
            (user["id"], body.message, reply, Jsonb(tools_used)),
        )

    return ChatResponse(reply=reply, tools_used=tools_used)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
