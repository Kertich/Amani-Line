create or replace function public.review_report(
  p_report_id uuid,
  p_update_status public.update_status,
  p_title text,
  p_detail text,
  p_source text default null
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
    and status in ('pending', 'reviewing')
  for update;

  if not found then
    raise exception 'Report not found or already reviewed';
  end if;

  insert into public.community_updates (status, title, detail, source)
  values (p_update_status, p_title, p_detail, p_source)
  returning * into published_update;

  update public.reports
  set status = 'resolved'
  where id = p_report_id;

  return jsonb_build_object(
    'community_update_id', published_update.id
  );
end;
$$;

revoke all on function public.review_report(uuid, public.update_status, text, text, text)
from public, anon, authenticated;
grant execute on function public.review_report(uuid, public.update_status, text, text, text)
to service_role;
