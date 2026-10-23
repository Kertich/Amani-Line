create or replace function public.flag_possible_report_duplicate()
returns trigger
language plpgsql
set search_path = public, extensions
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
