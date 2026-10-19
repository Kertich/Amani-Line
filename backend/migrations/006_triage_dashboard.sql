create extension if not exists pg_trgm;

alter table public.reports
  add column if not exists ward text,
  add column if not exists priority text not null default 'normal'
    check (priority in ('low', 'normal', 'urgent')),
  add column if not exists triage_notes text,
  add column if not exists first_response_at timestamptz,
  add column if not exists possible_duplicate_of uuid
    references public.reports(id) on delete set null;

alter table public.report_reviewers
  add column if not exists ward text,
  add column if not exists display_name text;

create index if not exists reports_ward_status_created_at_idx
  on public.reports (ward, status, created_at desc);

create index if not exists reports_description_trgm_idx
  on public.reports using gin (lower(description) gin_trgm_ops);

create index if not exists reports_possible_duplicate_of_idx
  on public.reports (possible_duplicate_of)
  where possible_duplicate_of is not null;

create table if not exists public.report_events (
  id uuid primary key default gen_random_uuid(),
  report_id uuid not null references public.reports(id) on delete cascade,
  actor_email text,
  action text not null,
  from_status text,
  to_status text,
  note text,
  created_at timestamptz not null default now()
);

create index if not exists report_events_report_created_idx
  on public.report_events (report_id, created_at);

alter table public.report_events enable row level security;
revoke all on public.report_events from anon, authenticated;

create or replace function public.audit_report_creation()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  insert into public.report_events (
    report_id, action, from_status, to_status, note
  ) values (
    new.id, 'created', null, new.status::text, new.channel
  );
  return new;
end;
$$;

drop trigger if exists reports_audit_creation on public.reports;
create trigger reports_audit_creation
after insert on public.reports
for each row execute function public.audit_report_creation();

create table if not exists public.dispute_events (
  id uuid primary key default gen_random_uuid(),
  dispute_id uuid not null references public.dispute_requests(id) on delete cascade,
  actor_email text,
  action text not null,
  from_status text,
  to_status text,
  note text,
  created_at timestamptz not null default now()
);

alter table public.dispute_requests
  add column if not exists resolution_path text
    check (resolution_path in ('elder_baraza', 'chief_office', 'landlord_association') or resolution_path is null),
  add column if not exists assigned_to_email text,
  add column if not exists triage_notes text;

create index if not exists dispute_events_dispute_created_idx
  on public.dispute_events (dispute_id, created_at);

alter table public.dispute_events enable row level security;
revoke all on public.dispute_events from anon, authenticated;

create or replace function public.audit_dispute_creation()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  insert into public.dispute_events (
    dispute_id, action, from_status, to_status
  ) values (
    new.id, 'created', null, new.status
  );
  return new;
end;
$$;

drop trigger if exists dispute_requests_audit_creation on public.dispute_requests;
create trigger dispute_requests_audit_creation
after insert on public.dispute_requests
for each row execute function public.audit_dispute_creation();

create or replace function public.flag_possible_report_duplicate()
returns trigger
language plpgsql
set search_path = 'public, extensions'
as $$
declare
  match_id uuid;
begin
  if new.ward is null or btrim(new.ward) = '' then
    new.possible_duplicate_of := null;
    return new;
  end if;

  select r.id
  into match_id
  from public.reports r
  where r.id <> new.id
    and r.ward = new.ward
    and r.status in ('pending', 'reviewing', 'needs_info')
    and lower(r.description) % lower(new.description)
    and similarity(lower(r.description), lower(new.description)) >= 0.42
  order by similarity(lower(r.description), lower(new.description)) desc,
    r.created_at desc
  limit 1;

  new.possible_duplicate_of := match_id;
  return new;
end;
$$;

drop trigger if exists reports_flag_possible_duplicate on public.reports;
create trigger reports_flag_possible_duplicate
before insert or update of ward, description on public.reports
for each row execute function public.flag_possible_report_duplicate();

create or replace function public.update_report_triage(
  p_report_id uuid,
  p_actor_email text,
  p_action text,
  p_priority text default null,
  p_ward text default null,
  p_notes text default null,
  p_reason text default null
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  selected_report public.reports%rowtype;
  updated_report public.reports%rowtype;
  next_status public.report_status;
begin
  if p_action not in ('triage', 'request_more_info', 'dismiss') then
    raise exception 'Invalid triage action';
  end if;
  if p_priority is not null and p_priority not in ('low', 'normal', 'urgent') then
    raise exception 'Invalid priority';
  end if;
  if p_action = 'dismiss' and nullif(btrim(p_reason), '') is null then
    raise exception 'A reason is required to dismiss a report';
  end if;

  select * into selected_report
  from public.reports
  where id = p_report_id
    and status in ('pending', 'reviewing', 'needs_info')
  for update;
  if not found then
    raise exception 'Report not found or already closed';
  end if;

  next_status := case
    when p_action = 'request_more_info' then 'needs_info'::public.report_status
    when p_action = 'dismiss' then 'dismissed'::public.report_status
    else selected_report.status
  end;

  update public.reports
  set priority = coalesce(p_priority, priority),
      ward = coalesce(nullif(btrim(p_ward), ''), ward),
      triage_notes = coalesce(
        nullif(btrim(p_notes), ''),
        nullif(btrim(p_reason), ''),
        triage_notes
      ),
      status = next_status,
      first_response_at = coalesce(first_response_at, now())
  where id = p_report_id
  returning * into updated_report;

  insert into public.report_events (
    report_id, actor_email, action, from_status, to_status, note
  ) values (
    p_report_id,
    lower(p_actor_email),
    p_action,
    selected_report.status::text,
    next_status::text,
    coalesce(nullif(btrim(p_reason), ''), nullif(btrim(p_notes), ''))
  );

  return jsonb_build_object(
    'id', updated_report.id,
    'reference', updated_report.reference,
    'status', updated_report.status,
    'ward', updated_report.ward,
    'priority', updated_report.priority,
    'triage_notes', updated_report.triage_notes,
    'first_response_at', updated_report.first_response_at
  );
end;
$$;

revoke all on function public.update_report_triage(uuid, text, text, text, text, text, text)
from public, anon, authenticated;
grant execute on function public.update_report_triage(uuid, text, text, text, text, text, text)
to service_role;

create or replace function public.assign_report(
  p_report_id uuid,
  p_actor_email text,
  p_assigned_to_email text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  selected_report public.reports%rowtype;
  updated_report public.reports%rowtype;
  next_status public.report_status;
begin
  select * into selected_report
  from public.reports
  where id = p_report_id
    and status in ('pending', 'reviewing', 'needs_info')
  for update;
  if not found then
    raise exception 'Report not found or already closed';
  end if;

  next_status := case
    when p_assigned_to_email is null then 'pending'::public.report_status
    else 'reviewing'::public.report_status
  end;

  update public.reports
  set assigned_to_email = p_assigned_to_email,
      status = next_status,
      first_response_at = case
        when p_assigned_to_email is null then first_response_at
        else coalesce(first_response_at, now())
      end
  where id = p_report_id
  returning * into updated_report;

  insert into public.report_events (
    report_id, actor_email, action, from_status, to_status, note
  ) values (
    p_report_id,
    lower(p_actor_email),
    case when p_assigned_to_email is null then 'unassigned' else 'assigned' end,
    selected_report.status::text,
    next_status::text,
    case
      when p_assigned_to_email is null then 'Returned to unassigned queue'
      else 'Assigned to ' || p_assigned_to_email
    end
  );

  return jsonb_build_object(
    'id', updated_report.id,
    'assigned_to_email', updated_report.assigned_to_email,
    'status', updated_report.status,
    'first_response_at', updated_report.first_response_at
  );
end;
$$;

revoke all on function public.assign_report(uuid, text, text)
from public, anon, authenticated;
grant execute on function public.assign_report(uuid, text, text)
to service_role;

create or replace function public.update_dispute(
  p_dispute_id uuid,
  p_actor_email text,
  p_resolution_path text default null,
  p_assigned_to_email text default null,
  p_status text default null,
  p_note text default null
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  selected_dispute public.dispute_requests%rowtype;
  updated_dispute public.dispute_requests%rowtype;
begin
  if p_resolution_path is not null and p_resolution_path not in (
    'elder_baraza', 'chief_office', 'landlord_association'
  ) then
    raise exception 'Invalid resolution path';
  end if;
  if p_status is not null and p_status not in ('scheduled', 'closed') then
    raise exception 'Invalid dispute status';
  end if;

  select * into selected_dispute
  from public.dispute_requests
  where id = p_dispute_id
  for update;
  if not found then
    raise exception 'Dispute not found';
  end if;
  if selected_dispute.status = 'closed' and p_status = 'scheduled' then
    raise exception 'A closed dispute cannot be rescheduled';
  end if;
  if p_status = 'scheduled'
    and coalesce(p_resolution_path, selected_dispute.resolution_path) is null then
    raise exception 'Choose a resolution path before scheduling';
  end if;

  update public.dispute_requests
  set resolution_path = coalesce(p_resolution_path, resolution_path),
      assigned_to_email = coalesce(p_assigned_to_email, assigned_to_email),
      status = coalesce(p_status, status),
      triage_notes = coalesce(nullif(btrim(p_note), ''), triage_notes)
  where id = p_dispute_id
  returning * into updated_dispute;

  if selected_dispute.resolution_path is distinct from updated_dispute.resolution_path then
    insert into public.dispute_events (
      dispute_id, actor_email, action, from_status, to_status, note
    ) values (
      p_dispute_id, lower(p_actor_email), 'routed',
      selected_dispute.status, updated_dispute.status,
      updated_dispute.resolution_path
    );
  end if;
  if selected_dispute.assigned_to_email is distinct from updated_dispute.assigned_to_email then
    insert into public.dispute_events (
      dispute_id, actor_email, action, from_status, to_status, note
    ) values (
      p_dispute_id, lower(p_actor_email), 'assigned',
      selected_dispute.status, updated_dispute.status,
      updated_dispute.assigned_to_email
    );
  end if;
  if selected_dispute.status is distinct from updated_dispute.status then
    insert into public.dispute_events (
      dispute_id, actor_email, action, from_status, to_status, note
    ) values (
      p_dispute_id, lower(p_actor_email), 'status_changed',
      selected_dispute.status, updated_dispute.status, p_note
    );
  elsif p_note is not null and btrim(p_note) <> '' then
    insert into public.dispute_events (
      dispute_id, actor_email, action, from_status, to_status, note
    ) values (
      p_dispute_id, lower(p_actor_email), 'note_added',
      selected_dispute.status, updated_dispute.status, p_note
    );
  end if;

  return jsonb_build_object(
    'id', updated_dispute.id,
    'status', updated_dispute.status,
    'resolution_path', updated_dispute.resolution_path,
    'assigned_to_email', updated_dispute.assigned_to_email,
    'triage_notes', updated_dispute.triage_notes
  );
end;
$$;

revoke all on function public.update_dispute(uuid, text, text, text, text, text)
from public, anon, authenticated;
grant execute on function public.update_dispute(uuid, text, text, text, text, text)
to service_role;

drop function if exists public.review_report(
  uuid, public.update_status, text, text, text
);

create or replace function public.review_report(
  p_report_id uuid,
  p_update_status public.update_status,
  p_title text,
  p_detail text,
  p_source text default null,
  p_actor_email text default null
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  selected_report public.reports%rowtype;
  published_update public.community_updates%rowtype;
begin
  if p_update_status not in ('confirmed', 'false') then
    raise exception 'A report can only be published as confirmed or false';
  end if;

  select *
  into selected_report
  from public.reports
  where id = p_report_id
    and status in ('pending', 'reviewing', 'needs_info')
  for update;

  if not found then
    raise exception 'Report not found or already reviewed';
  end if;

  insert into public.community_updates (status, title, detail, source)
  values (p_update_status, p_title, p_detail, p_source)
  returning * into published_update;

  update public.reports
  set status = 'resolved',
      first_response_at = coalesce(first_response_at, now())
  where id = p_report_id;

  insert into public.report_events (
    report_id, actor_email, action, from_status, to_status, note
  ) values (
    p_report_id,
    coalesce(p_actor_email, 'unknown'),
    'published',
    selected_report.status::text,
    'resolved',
    p_title
  );

  return jsonb_build_object('community_update_id', published_update.id);
end;
$$;

revoke all on function public.review_report(uuid, public.update_status, text, text, text, text)
from public, anon, authenticated;
grant execute on function public.review_report(uuid, public.update_status, text, text, text, text)
to service_role;
