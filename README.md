# Lecture 7 Project

A full-stack application with React + Vite + TypeScript frontend and FastAPI backend.

## Project Structure

```
Lecture 7/
├── frontend/           # React + Vite + TypeScript
│   ├── src/
│   │   ├── App.tsx
│   │   ├── App.css
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── index.html
└── backend/            # FastAPI
    ├── main.py
    ├── requirements.txt
    └── .env.example
```

## Setup

### Backend

1. Create a virtual environment:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` from `.env.example` and set `SECRET_KEY` (it signs sign-in tokens):
```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"
```

4. Run the server:
```bash
python main.py
```

The API will be available at `http://localhost:8000`  
Docs: `http://localhost:8000/docs`

### Frontend

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Run the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

## Development

The frontend is configured to proxy API requests to the backend via `/api` routes.

- Frontend runs on `http://localhost:5173`
- Backend runs on `http://localhost:8000`
- API docs available at `http://localhost:8000/docs`

## Database and accounts

Data lives in SQLite at `data/yale_som.db`:

- `courses` – the course catalog; both the course cards (`/api/courses`) and the chat agent's
  `search_courses` tool read from it. Session dates and enrollment type were added with
  `python backend/migrate_course_details.py`, which copies them from the original JSON.
- `users` – accounts; passwords are stored as bcrypt hashes (the salt is part of the hash)
- `chats` – each signed-in user's questions and the assistant's replies

`users` and `chats` are created automatically when the backend starts. Signing in returns a
token the frontend sends as `Authorization: Bearer <token>`; `/api/chat` and `/api/chats`
require it.
