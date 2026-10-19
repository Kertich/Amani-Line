alter table public.report_reviewers
  add column if not exists role text not null default 'reviewer';

update public.report_reviewers
set role = 'ward_admin'
where ward is not null and btrim(ward) <> '' and role = 'reviewer';

alter table public.report_reviewers
  add constraint report_reviewers_role_check
  check (role in ('reviewer', 'ward_admin'));

alter table public.report_reviewers
  add constraint report_reviewers_ward_admin_ward_check
  check (role <> 'ward_admin' or nullif(btrim(ward), '') is not null);

alter table public.community_updates
  add column if not exists workflow_status text not null default 'draft'
    check (workflow_status in ('draft', 'pending_approval', 'published', 'rejected', 'corrected', 'retracted')),
  add column if not exists author_email text,
  add column if not exists approved_by_email text,
  add column if not exists published_at timestamptz,
  add column if not exists evidence_url text,
  add column if not exists evidence_note text,
  add column if not exists verification_method text
    constraint community_updates_verification_method_value_check
    check (verification_method in ('official_notice', 'first_hand_witness', 'multiple_community_sources')),
  add column if not exists publisher_label text,
  add column if not exists source_report_id uuid references public.reports(id) on delete set null;

create index if not exists community_updates_source_report_idx
  on public.community_updates (source_report_id)
  where source_report_id is not null;

create unique index if not exists community_updates_pending_report_idx
  on public.community_updates (source_report_id)
  where source_report_id is not null and workflow_status = 'pending_approval';

create table if not exists public.community_update_events (
  id uuid primary key default gen_random_uuid(),
  community_update_id uuid not null references public.community_updates(id) on delete restrict,
  actor_email text not null,
  actor_label text not null,
  action text not null check (action in (
    'draft_submitted', 'approved', 'published_directly', 'rejected', 'corrected', 'retracted'
  )),
  reason text,
  created_at timestamptz not null default now()
);

create index if not exists community_update_events_history_idx
  on public.community_update_events (community_update_id, created_at);

alter table public.community_update_events enable row level security;
revoke all on public.community_update_events from anon, authenticated;
revoke all on public.community_updates from public, anon, authenticated;
drop policy if exists "Anyone can read community updates" on public.community_updates;

alter table public.community_updates
  add constraint community_updates_finding_source_check
  check (
    status not in ('confirmed', 'false')
    or nullif(btrim(source), '') is not null
  )
  not valid;

alter table public.community_updates
  add constraint community_updates_evidence_check
  check (
    nullif(btrim(evidence_url), '') is not null
    or nullif(btrim(evidence_note), '') is not null
  )
  not valid;

alter table public.community_updates
  add constraint community_updates_verification_method_check
  check (verification_method is not null)
  not valid;

alter table public.community_updates
  add constraint community_updates_author_check
  check (nullif(btrim(author_email), '') is not null)
  not valid;

alter table public.community_updates
  add constraint community_updates_published_attribution_check
  check (
    workflow_status not in ('published', 'corrected', 'retracted')
    or (
      nullif(btrim(author_email), '') is not null
      and nullif(btrim(approved_by_email), '') is not null
      and published_at is not null
      and nullif(btrim(publisher_label), '') is not null
    )
  )
  not valid;

drop view if exists public.public_community_updates;
create view public.public_community_updates as
select
  u.id,
  u.status,
  u.workflow_status,
  u.title,
  u.detail,
  u.source,
  u.published_at,
  u.verification_method,
  u.publisher_label,
  greatest(u.published_at, max(e.created_at)) as activity_at,
  coalesce(
    jsonb_agg(
      jsonb_build_object(
        'action', e.action,
        'reason', e.reason,
        'created_at', e.created_at,
        'actor_label', e.actor_label
      ) order by e.created_at
    ) filter (where e.id is not null),
    '[]'::jsonb
  ) as correction_history,
  (array_agg(e.reason order by e.created_at desc)
    filter (where e.action in ('corrected', 'retracted')))[1] as correction_reason
from public.community_updates u
left join public.community_update_events e on e.community_update_id = u.id
where u.workflow_status in ('published', 'corrected', 'retracted')
  and u.author_email is not null
  and u.approved_by_email is not null
  and u.published_at is not null
  and nullif(btrim(u.publisher_label), '') is not null
group by u.id;

revoke all on public.public_community_updates from public, anon, authenticated;
grant select on public.public_community_updates to service_role;

create or replace function public.guard_community_update_immutability()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_op = 'DELETE' then
    raise exception 'Community updates are retained for accountability';
  end if;
  if row(
    new.status, new.title, new.detail, new.source, new.author_email,
    new.verification_method, new.evidence_url, new.evidence_note,
    new.source_report_id, new.created_at
  ) is distinct from row(
    old.status, old.title, old.detail, old.source, old.author_email,
    old.verification_method, old.evidence_url, old.evidence_note,
    old.source_report_id, old.created_at
  ) then
    raise exception 'Community update content is immutable; record a correction instead';
  end if;
  if (old.workflow_status = 'draft' and new.workflow_status not in ('pending_approval', 'published'))
    or (old.workflow_status = 'pending_approval' and new.workflow_status not in ('published', 'rejected'))
    or (old.workflow_status = 'published' and new.workflow_status not in ('corrected', 'retracted'))
    or (old.workflow_status = 'corrected' and new.workflow_status not in ('corrected', 'retracted'))
    or old.workflow_status in ('rejected', 'retracted') then
    raise exception 'Invalid community update state transition';
  end if;
  if new.workflow_status not in ('published', 'corrected', 'retracted')
    and row(new.approved_by_email, new.published_at, new.publisher_label)
      is distinct from row(old.approved_by_email, old.published_at, old.publisher_label) then
    raise exception 'Only publication may set approver and publisher details';
  end if;
  if old.workflow_status in ('published', 'corrected', 'retracted')
    and row(new.approved_by_email, new.published_at, new.publisher_label)
      is distinct from row(old.approved_by_email, old.published_at, old.publisher_label) then
    raise exception 'Published attribution is immutable';
  end if;
  return new;
end;
$$;

drop trigger if exists community_updates_immutable on public.community_updates;
create trigger community_updates_immutable
before update or delete on public.community_updates
for each row execute function public.guard_community_update_immutability();

drop function if exists public.review_report(
  uuid, public.update_status, text, text, text, text
);

create or replace function public.review_report(
  p_report_id uuid,
  p_update_status public.update_status,
  p_title text,
  p_detail text,
  p_source text,
  p_actor_email text,
  p_action text,
  p_verification_method text,
  p_evidence_url text,
  p_evidence_note text,
  p_publisher_label text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  selected_report public.reports%rowtype;
  new_update public.community_updates%rowtype;
  target_workflow text;
  event_action text;
begin
  if p_update_status is null or p_update_status not in ('confirmed', 'false') then
    raise exception 'A report can only be submitted as confirmed or false';
  end if;
  if nullif(btrim(p_source), '') is null then
    raise exception 'A source is required for confirmed or false findings';
  end if;
  if nullif(btrim(p_actor_email), '') is null
    or nullif(btrim(p_publisher_label), '') is null then
    raise exception 'A traceable author and publisher label are required';
  end if;
  if nullif(btrim(p_evidence_url), '') is null
    and nullif(btrim(p_evidence_note), '') is null then
    raise exception 'An evidence URL or note is required';
  end if;
  if p_action is null or p_action not in ('submit', 'publish_directly') then
    raise exception 'Invalid update submission action';
  end if;
  if p_verification_method is null or p_verification_method not in (
    'official_notice', 'first_hand_witness', 'multiple_community_sources'
  ) then
    raise exception 'Invalid verification method';
  end if;
  if nullif(btrim(p_title), '') is null or nullif(btrim(p_detail), '') is null then
    raise exception 'An update title and detail are required';
  end if;

  select * into selected_report
  from public.reports
  where id = p_report_id and status in ('pending', 'reviewing', 'needs_info')
  for update;
  if not found then
    raise exception 'Report not found or already reviewed';
  end if;

  target_workflow := case when p_action = 'submit' then 'pending_approval' else 'published' end;
  event_action := case when p_action = 'submit' then 'draft_submitted' else 'published_directly' end;

  insert into public.community_updates (
    status, title, detail, source, workflow_status, author_email,
    approved_by_email, published_at, verification_method, evidence_url,
    evidence_note, publisher_label, source_report_id
  ) values (
    p_update_status, btrim(p_title), btrim(p_detail), nullif(btrim(p_source), ''),
    'draft', lower(btrim(p_actor_email)),
    case when p_action = 'publish_directly' then lower(btrim(p_actor_email)) else null end,
    case when p_action = 'publish_directly' then now() else null end,
    p_verification_method, nullif(btrim(p_evidence_url), ''),
    nullif(btrim(p_evidence_note), ''),
    case when p_action = 'publish_directly' then btrim(p_publisher_label) else null end,
    p_report_id
  ) returning * into new_update;

  update public.community_updates
  set workflow_status = target_workflow
  where id = new_update.id;

  if p_action = 'publish_directly' then
    update public.reports
    set status = 'resolved', first_response_at = coalesce(first_response_at, now())
    where id = p_report_id;
  end if;

  insert into public.community_update_events (
    community_update_id, actor_email, actor_label, action
  ) values (
    new_update.id, lower(btrim(p_actor_email)), btrim(p_publisher_label), event_action
  );

  insert into public.report_events (
    report_id, actor_email, action, from_status, to_status, note
  ) values (
    p_report_id, lower(btrim(p_actor_email)), event_action,
    selected_report.status::text,
    case when p_action = 'publish_directly' then 'resolved' else selected_report.status::text end,
    new_update.id::text
  );

  return jsonb_build_object(
    'community_update_id', new_update.id,
    'workflow_status', target_workflow
  );
end;
$$;

create or replace function public.moderate_community_update(
  p_update_id uuid,
  p_actor_email text,
  p_actor_label text,
  p_action text,
  p_reason text default null,
  p_publisher_label text default null
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  selected_update public.community_updates%rowtype;
  selected_report public.reports%rowtype;
  next_workflow text;
begin
  if p_action not in ('approve', 'reject', 'correct', 'retract') then
    raise exception 'Invalid update moderation action';
  end if;
  if nullif(btrim(p_actor_email), '') is null
    or nullif(btrim(p_actor_label), '') is null then
    raise exception 'A traceable moderator is required';
  end if;
  if p_action in ('reject', 'correct', 'retract')
    and nullif(btrim(p_reason), '') is null then
    raise exception 'A reason is required';
  end if;

  select * into selected_update
  from public.community_updates
  where id = p_update_id
  for update;
  if not found then
    raise exception 'Update not found';
  end if;

  if p_action = 'approve' then
    if selected_update.workflow_status <> 'pending_approval' then
      raise exception 'Only pending updates can be approved';
    end if;
    if lower(selected_update.author_email) = lower(btrim(p_actor_email)) then
      raise exception 'The author cannot approve their own update';
    end if;
    if selected_update.status in ('confirmed', 'false')
      and nullif(btrim(selected_update.source), '') is null then
      raise exception 'A source is required for confirmed or false findings';
    end if;
    if nullif(btrim(p_publisher_label), '') is null then
      raise exception 'A public publisher label is required';
    end if;
    next_workflow := 'published';
    update public.community_updates
    set workflow_status = next_workflow,
        approved_by_email = lower(btrim(p_actor_email)),
        published_at = now(),
        publisher_label = btrim(p_publisher_label)
    where id = p_update_id;
  elsif p_action = 'reject' then
    if selected_update.workflow_status <> 'pending_approval' then
      raise exception 'Only pending updates can be rejected';
    end if;
    if lower(selected_update.author_email) = lower(btrim(p_actor_email)) then
      raise exception 'The author cannot reject their own update';
    end if;
    next_workflow := 'rejected';
    update public.community_updates set workflow_status = next_workflow
    where id = p_update_id;
  else
    if selected_update.workflow_status not in ('published', 'corrected') then
      raise exception 'Only published updates can be corrected or retracted';
    end if;
    next_workflow := case when p_action = 'correct' then 'corrected' else 'retracted' end;
    update public.community_updates set workflow_status = next_workflow
    where id = p_update_id;
  end if;

  insert into public.community_update_events (
    community_update_id, actor_email, actor_label, action, reason
  ) values (
    p_update_id, lower(btrim(p_actor_email)), btrim(p_actor_label),
    case p_action
      when 'approve' then 'approved'
      when 'reject' then 'rejected'
      when 'correct' then 'corrected'
      else 'retracted'
    end,
    case when p_action = 'approve' then null else btrim(p_reason) end
  );

  if selected_update.source_report_id is not null then
    select * into selected_report
    from public.reports
    where id = selected_update.source_report_id
    for update;
    if found then
      if p_action = 'approve'
        and selected_report.status in ('pending', 'reviewing', 'needs_info') then
        update public.reports
        set status = 'resolved', first_response_at = coalesce(first_response_at, now())
        where id = selected_report.id;
      end if;
      insert into public.report_events (
        report_id, actor_email, action, from_status, to_status, note
      ) values (
        selected_report.id, lower(btrim(p_actor_email)), p_action,
        selected_report.status::text,
        case when p_action = 'approve'
          and selected_report.status in ('pending', 'reviewing', 'needs_info')
          then 'resolved' else selected_report.status::text end,
        coalesce(nullif(btrim(p_reason), ''), p_update_id::text)
      );
    end if;
  end if;

  return jsonb_build_object('id', p_update_id, 'workflow_status', next_workflow);
end;
$$;

revoke all on function public.review_report(
  uuid, public.update_status, text, text, text, text, text, text, text, text, text
) from public, anon, authenticated;
grant execute on function public.review_report(
  uuid, public.update_status, text, text, text, text, text, text, text, text, text
) to service_role;

revoke all on function public.moderate_community_update(uuid, text, text, text, text, text)
from public, anon, authenticated;
grant execute on function public.moderate_community_update(uuid, text, text, text, text, text)
to service_role;
