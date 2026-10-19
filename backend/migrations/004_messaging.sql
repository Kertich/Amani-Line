alter table public.reports
  add column if not exists channel text not null default 'web'
    check (channel in ('web', 'ussd', 'sms')),
  add column if not exists reporter_hash text,
  add column if not exists language text
    check (language in ('en', 'sw') or language is null);

create table if not exists public.reporter_contacts (
  reporter_hash text primary key,
  encrypted_phone text not null,
  language text not null default 'en' check (language in ('en', 'sw')),
  updated_at timestamptz not null default now()
);

alter table public.reporter_contacts enable row level security;
revoke all on public.reporter_contacts from anon, authenticated;
