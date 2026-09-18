# Amani Line API

FastAPI backend using Supabase Auth, Postgres, and Storage.

## Setup

1. Create a Supabase project.
2. Run `schema.sql` in the Supabase SQL editor.
3. Copy `.env.example` to `.env` and add the project URL, anon key, and service-role key.
4. Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

5. Start the API:

```powershell
uvicorn app.main:app --reload
```

The interactive API docs are available at `http://localhost:8000/docs`.

## Endpoints

- `POST /api/auth/signup` and `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/reports` (anonymous or authenticated)
- `GET /api/updates?status=confirmed`
- `POST /api/disputes` (authenticated)
- `POST /api/storage/upload-url` (authenticated)
