create extension if not exists pgcrypto;

create type report_status as enum ('pending', 'reviewing', 'resolved', 'dismissed');
create type update_status as enum ('confirmed', 'pending', 'false');

create table if not exists public.reports (
  id uuid primary key default gen_random_uuid(),
  reference text not null unique default ('AMN-' || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 6))),
  user_id uuid references auth.users(id) on delete set null,
  report_type text not null check (report_type in ('Rumour to check', 'Local issue', 'Safety concern')),
  description text not null check (char_length(description) between 1 and 5000),
  attachment_path text,
  status report_status not null default 'pending',
  created_at timestamptz not null default now(),
  ai_language text,
  ai_normalized_text text,
  ai_category text,
  ai_confidence double precision,
  ai_dispute_category text,
  ai_summary text,
  ai_review_required boolean not null default false,
  ai_review_reason text,
  ai_pii_flagged boolean not null default false,
  ai_duplicate_of uuid references public.reports(id) on delete set null
);

create table if not exists public.community_updates (
  id uuid primary key default gen_random_uuid(),
  status update_status not null default 'pending',
  title text not null,
  detail text not null,
  source text,
  created_at timestamptz not null default now()
);

create table if not exists public.dispute_requests (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  concern_type text not null,
  desired_outcome text not null,
  contact_phone text,
  status text not null default 'received',
  created_at timestamptz not null default now()
);

insert into storage.buckets (id, name, public)
values ('report-attachments', 'report-attachments', false)
on conflict (id) do nothing;

alter table public.reports enable row level security;
alter table public.community_updates enable row level security;
alter table public.dispute_requests enable row level security;

create policy "Anyone can read community updates"
on public.community_updates for select using (true);

create policy "Users can read their own reports"
on public.reports for select using (auth.uid() = user_id);

create policy "Users can read their own disputes"
on public.dispute_requests for select using (auth.uid() = user_id);

create policy "Users can manage their own attachments"
on storage.objects for all using (
  bucket_id = 'report-attachments' and (storage.foldername(name))[1] = auth.uid()::text
) with check (
  bucket_id = 'report-attachments' and (storage.foldername(name))[1] = auth.uid()::text
);
