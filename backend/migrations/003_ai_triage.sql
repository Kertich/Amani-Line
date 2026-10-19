alter table public.reports
  add column if not exists ai_language text,
  add column if not exists ai_normalized_text text,
  add column if not exists ai_category text,
  add column if not exists ai_confidence double precision,
  add column if not exists ai_dispute_category text,
  add column if not exists ai_summary text,
  add column if not exists ai_review_required boolean not null default false,
  add column if not exists ai_review_reason text,
  add column if not exists ai_pii_flagged boolean not null default false,
  add column if not exists ai_duplicate_of uuid references public.reports(id) on delete set null;

create index if not exists reports_ai_duplicate_of_idx
  on public.reports (ai_duplicate_of)
  where ai_duplicate_of is not null;

create index if not exists reports_ai_private_escalations_idx
  on public.reports (created_at)
  where ai_pii_flagged = true;
