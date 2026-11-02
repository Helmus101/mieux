-- Run once in Supabase: SQL Editor > New query > paste > Run.
-- The only thing stored per account: how many scans. The app counts on the device and writes ONCE A WEEK; it never reads this table.

create table if not exists public.scan_counts (
  user_id uuid primary key references auth.users (id) on delete cascade,
  scans integer not null default 0 check (scans >= 0),
  updated_at timestamptz not null default now()
);

alter table public.scan_counts enable row level security;

-- No policies: nobody can read or write the table directly from the app. Writes go through add_scans() only.
drop policy if exists "read own scan count" on public.scan_counts;

drop function if exists public.increment_scans();

-- Adds n scans to the signed-in user's total. Returns nothing (no egress).
create or replace function public.add_scans(n integer) returns void
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'not signed in'; end if;
  if n is null or n < 1 or n > 100000 then raise exception 'invalid count'; end if;
  insert into public.scan_counts (user_id, scans) values (auth.uid(), n)
  on conflict (user_id) do update set scans = public.scan_counts.scans + excluded.scans, updated_at = now();
end;
$$;

revoke all on function public.add_scans(integer) from public, anon;
grant execute on function public.add_scans(integer) to authenticated;

-- To see everyone's totals (SQL editor): select u.email, c.scans from public.scan_counts c join auth.users u on u.id = c.user_id order by c.scans desc;
