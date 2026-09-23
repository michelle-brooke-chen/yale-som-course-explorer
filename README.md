# Yale SOM Course Explorer

Browse Yale School of Management's Fall 2026 courses and ask a chat assistant about them.
Built with a React + Vite + TypeScript frontend and a FastAPI backend for AI Foundations, Lecture 8.

## Project Structure

```
yale-som-course-explorer/
├── frontend/              # React + Vite + TypeScript
│   ├── src/
│   │   ├── App.tsx        # Sign-in gate and course catalog
│   │   ├── AuthScreen.tsx # Sign in / create account
│   │   ├── ChatPanel.tsx  # Course assistant with saved chats
│   │   ├── CourseCard.tsx
│   │   ├── CourseModal.tsx
│   │   └── api.ts
│   ├── index.html
│   └── package.json
├── backend/               # FastAPI
│   ├── main.py            # API routes
│   ├── agent.py           # Chat assistant
│   ├── tools.py           # search_courses tool
│   ├── auth.py            # bcrypt passwords and sign-in tokens
│   ├── db.py              # Database connection and tables
│   ├── seed_database.py   # Creates tables and loads courses into Supabase
│   ├── prompts/prompt.md
│   ├── requirements.txt
│   └── .env.example
└── data/
    └── yale_som_classes.json
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

3. Create `.env` from `.env.example`, then fill in:
   - `SECRET_KEY` – signs sign-in tokens; generate one with the command below
   - `DATABASE_URL` – your Supabase connection string (see [Database and accounts](#database-and-accounts))
```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"
```

4. Create the tables and load the courses (first time only):
```bash
python seed_database.py
```

5. Run the server:
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

Data lives in a Postgres database on [Supabase](https://supabase.com):

- `courses` – the course catalog; both the course cards (`/api/courses`) and the chat agent's
  `search_courses` tool read from it
- `users` – accounts; passwords are stored as bcrypt hashes (the salt is part of the hash)
- `chats` – each signed-in user's questions and the assistant's replies

To connect, open your Supabase project and click **Connect**, then copy the **Session pooler**
connection string (URI format), replace `[YOUR-PASSWORD]` with your database password, and set
it as `DATABASE_URL` in `backend/.env`. The session pooler works on IPv4 networks; the direct
connection needs IPv6.

`seed_database.py` creates the tables, loads `courses` from `data/yale_som_classes.json`, and
copies any users and chats from an older local SQLite file (`data/yale_som.db`) if one exists.
Row-level security is turned on for all three tables with no policies, so Supabase's public
Data API can't read them; the backend's direct database connection is unaffected.

Signing in returns a token the frontend sends as `Authorization: Bearer <token>`;
`/api/chat` and `/api/chats` require it.
