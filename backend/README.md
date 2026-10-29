# Amani Line API

FastAPI backend using Supabase Auth, Postgres, and Storage.

## Setup

1. Create a Supabase project.
2. Run `schema.sql` in the Supabase SQL editor.
3. Run `migrations/001_report_verification.sql` in the Supabase SQL editor.
4. Run `migrations/002_admin_reviewers.sql` in the Supabase SQL editor.
5. Run `migrations/003_ai_triage.sql` in the Supabase SQL editor.
6. Run `migrations/004_messaging.sql` in the Supabase SQL editor.
7. Run `migrations/005_needs_info_status.sql` in the Supabase SQL editor.
8. Run `migrations/006_triage_dashboard.sql` in the Supabase SQL editor.
9. Run `migrations/007_accountable_updates.sql` in the Supabase SQL editor. Existing updates without traceable author and publisher fields are kept out of the public feed; re-enter them as new report updates to publish them with accountable attribution.
10. Copy `.env.example` to `.env` and add the project URL, anon key, and service-role key.
    Configure Africa's Talking sandbox values for `AT_CALLBACK_SECRET`, `AT_API_KEY`, `AT_USERNAME=sandbox`, `AT_SMS_URL=https://api.sandbox.africastalking.com/version1/messaging`, `REPORTER_HMAC_PEPPER`, and `REPORTER_PHONE_ENCRYPTION_KEY`. The sandbox SMS URL is the default; keep it for testing and only use the production URL when switching to a live account.
11. Create a virtual environment and install dependencies from `pyproject.toml`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[test]"
```

12. Start the API:

```powershell
uvicorn main:app --reload
```

The interactive API docs are available at `http://localhost:8000/docs`.

## Africa's Talking sandbox + ngrok

For USSD and SMS callbacks, expose the local API on a public URL and point Africa's Talking to that URL in the sandbox. A typical flow is:

1. Start the API locally with `uvicorn main:app --reload`.
2. Forward localhost:8000 with `ngrok http 8000` and copy the HTTPS URL.
3. Set `AT_CALLBACK_SECRET` to a shared secret, then append it to each callback URL as `?secret=<url-encoded-secret>`; the API also accepts it in an `X-AT-Secret` header for local testing.
4. Configure the Africa's Talking USSD callback URL to `<ngrok-url>/api/ussd?secret=<url-encoded-secret>` and the inbound SMS callback URL to `<ngrok-url>/api/sms/inbound?secret=<url-encoded-secret>`. In the sandbox dashboard, configure the USSD service code and inbound SMS callback separately.
5. For a real sandbox test, send a request like:

```powershell
curl -X POST "http://localhost:8000/api/ussd" \
  -H "X-AT-Secret: secret" \
  --data "sessionId=123&serviceCode=*384*123#&phoneNumber=+254700000001&networkCode=&text=1*2*1*Fire near the market"
```

Use the same shared secret for the inbound SMS route. Keep response text short and use `CON ` / `END ` prefixes for USSD screens.

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
frontend. A reviewer with a ward set in reviewer access management becomes a
ward-scoped manager; the API limits their report queue, detail, triage, publish,
and assignment access to that ward. Website reports ask for a ward and route
to matching ward-scoped reviewers; the reporter must use the same ward name
configured for those reviewers. Reports received through SMS or USSD without a
ward remain visible only to global administrators until routed. Reviewers
without a ward can read and publish only reports assigned to their email
address. `ADMIN_EMAILS` and `VERIFICATION_QUEUE_EMAILS` are bootstrap
allowlists; manage ongoing reviewer access through the administrator interface.
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
- `GET /api/reports/queue` (scoped queue with filters, pagination, SLA age, and ward-safe possible duplicates)
- `GET /api/reports/{report_id}/events` and `PATCH /api/reports/{report_id}/triage` (authorized reviewer or ward manager)
- `GET /api/reports/reviewers` (global or ward-scoped assignment list)
- `GET /api/admin/reports/pii-escalations` and `POST /api/admin/reports/{report_id}/pii-clear` (administrator)
- `POST /api/voice-notes/transcribe` (authorized verifier, configured AI provider)
- `POST /api/reports/{report_id}/publish` (reviewers submit for approval; administrators publish directly)
- `GET /api/updates/pending`, `POST /api/updates/{update_id}/approve`, and `POST /api/updates/{update_id}/reject` (administrator or ward administrator; approval requires a different author)
- `POST /api/updates/{update_id}/correction` (record a reasoned correction or retraction; original content is retained)
- `GET /api/admin/reviewers`, `POST /api/admin/reviewers`, and `DELETE /api/admin/reviewers/{email}` (administrator)
- `PATCH /api/admin/reports/{report_id}/assignment` (global or ward-scoped manager)
- `GET /api/admin/disputes` and `PATCH /api/admin/disputes/{dispute_id}` (administrator)
- `GET /api/updates?status=confirmed` (public-safe publisher attribution and correction history; never author/approver email)
- `POST /api/disputes` (authenticated)
- `POST /api/storage/upload-url` (authenticated)
