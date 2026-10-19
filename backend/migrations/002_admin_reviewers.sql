create table if not exists public.report_reviewers (
  email text primary key,
  created_at timestamptz not null default now(),
  constraint report_reviewers_email_lowercase check (email = lower(email))
);

alter table public.report_reviewers enable row level security;
revoke all on public.report_reviewers from anon, authenticated;

alter table public.reports
  add column if not exists assigned_to_email text;

create index if not exists reports_assigned_to_status_created_at_idx
  on public.reports (assigned_to_email, status, created_at);
