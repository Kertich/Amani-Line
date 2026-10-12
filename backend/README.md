# Amani Line API

FastAPI backend using Supabase Auth, Postgres, and Storage.

## Setup

1. Create a Supabase project.
2. Run `schema.sql` in the Supabase SQL editor.
3. Run `migrations/001_report_verification.sql` in the Supabase SQL editor.
4. Run `migrations/002_admin_reviewers.sql` in the Supabase SQL editor.
5. Copy `.env.example` to `.env` and add the project URL, anon key, and service-role key.
6. Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

7. Start the API:

```powershell
uvicorn backend.main:app --reload
```

The interactive API docs are available at `http://localhost:8000/docs`.

## Frontend integration

In `frontend`, copy `.env.example` to `.env` and set `VITE_API_BASE_URL` to the
API origin (for example, `http://localhost:8000`). Then install dependencies
with `npm install` and start the development server with `npm run dev`.

The frontend uses this API for community updates, reports, account signup and
sign-in, and authenticated dispute requests. The default CORS origin permits
the Vite development server at `http://localhost:5173`; add any other frontend
origins to `CORS_ORIGINS` in the backend environment.

Set `VERIFICATION_QUEUE_EMAILS` to a comma-separated list of trusted verifier
email addresses. Only those accounts can read the verification queue or publish
reports; this is enforced by the API even if someone bypasses the frontend.
Set `ADMIN_EMAILS` to a comma-separated list of trusted administrator email
addresses. Administrators can authorize reviewers and assign reports from the
frontend; only administrators can change grants or assignments. Verifiers can
read and publish only reports assigned to their email address. `ADMIN_EMAILS`
and `VERIFICATION_QUEUE_EMAILS` are bootstrap allowlists; manage ongoing
reviewer access through the administrator interface.
Bootstrap administrator addresses must also have accounts in Supabase Auth.
Reviewers need to register/sign in using the exact email address an admin
authorizes.
Publishing is performed transactionally by the `review_report` database
function: it creates the community update and marks the original report
resolved together.

## Endpoints

- `POST /api/auth/signup` and `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/reports` (anonymous or authenticated)
- `GET /api/reports/queue` (assigned reviewer or administrator)
- `POST /api/reports/{report_id}/publish` (assigned reviewer or administrator; publishes a confirmed/false community update)
- `GET /api/admin/reviewers`, `POST /api/admin/reviewers`, and `DELETE /api/admin/reviewers/{email}` (administrator)
- `PATCH /api/admin/reports/{report_id}/assignment` (administrator)
- `GET /api/updates?status=confirmed`
- `POST /api/disputes` (authenticated)
- `POST /api/storage/upload-url` (authenticated)
