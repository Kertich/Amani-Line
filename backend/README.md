# Amani Line API

FastAPI backend using Supabase Auth, Postgres, and Storage.

## Setup

1. Create a Supabase project.
2. Run `schema.sql` in the Supabase SQL editor.
3. Run `migrations/001_report_verification.sql` in the Supabase SQL editor.
4. Run `migrations/002_admin_reviewers.sql` in the Supabase SQL editor.
5. Run `migrations/003_ai_triage.sql` in the Supabase SQL editor.
6. Copy `.env.example` to `.env` and add the project URL, anon key, and service-role key.
7. Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

8. Start the API:

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

## AI-assisted triage

AI triage is optional. To enable contextual English, Swahili, and Sheng
normalization/classification, plain-language draft summaries, and voice-note
transcription, configure `AI_API_KEY`, `AI_BASE_URL`, `AI_CHAT_MODEL`, and
`AI_TRANSCRIPTION_MODEL` in the backend environment. The adapter uses the
OpenAI-compatible chat-completions and audio-transcriptions endpoints. Without
an AI key, English/Swahili messages use conservative local rules; Sheng,
code-switched, unsupported, and uncertain messages are sent to human review
without an AI category. When enabled, report text and validator-uploaded audio
are sent to the configured AI provider. Choose a provider and data-retention
settings appropriate for sensitive community reports.

Every AI summary and category is a draft recommendation. AI never publishes,
marks a rumour true/false, or replaces human review. Reports that match local
rules for named allegations or contact details are stored as private
escalations, are excluded from the normal reviewer queue, are not sent to the
AI provider, and cannot be published until an administrator supplies a
redacted version. Administrators can view them at
`GET /api/admin/reports/pii-escalations`; return a redacted report with
`POST /api/admin/reports/{report_id}/pii-clear`.

Similar reports submitted within 14 days are linked to the earliest matching
report and grouped in the reviewer queue. Validators can upload a voice note
for transcription at `POST /api/voice-notes/transcribe` (multipart field
`file`); the endpoint is limited to authorized verifiers and 20 MB. It returns
text for review and does not save or publish the audio/transcript. A WhatsApp
webhook/media-download integration is not configured in this repository;
connect that integration to the transcription endpoint separately.

## Endpoints

- `POST /api/auth/signup` and `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/reports` (anonymous or authenticated)
- `GET /api/reports/queue` (assigned reviewer or administrator)
- `GET /api/admin/reports/pii-escalations` and `POST /api/admin/reports/{report_id}/pii-clear` (administrator)
- `POST /api/voice-notes/transcribe` (authorized verifier, configured AI provider)
- `POST /api/reports/{report_id}/publish` (assigned reviewer or administrator; publishes a confirmed/false community update)
- `GET /api/admin/reviewers`, `POST /api/admin/reviewers`, and `DELETE /api/admin/reviewers/{email}` (administrator)
- `PATCH /api/admin/reports/{report_id}/assignment` (administrator)
- `GET /api/updates?status=confirmed`
- `POST /api/disputes` (authenticated)
- `POST /api/storage/upload-url` (authenticated)
