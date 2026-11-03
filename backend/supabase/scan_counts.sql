-- Run once in Supabase: SQL Editor > New query > paste > Run.
-- The only thing stored per account: how many scans. The app adds each scan as it happens (write-only) and never reads this table.

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


-- =====================================================================================================
-- Admin: totals. Only the people listed in public.admins can use this.
-- Admin is pinned to the account's user id, not to an email: with "Confirm email" off, anyone could type your email at sign-up
-- BEFORE you do. So sign up with tjong.willem@gmail.com first, then run the insert below.
-- =====================================================================================================
create table if not exists public.admins (user_id uuid primary key references auth.users (id) on delete cascade);
alter table public.admins enable row level security;   -- no policies: only the functions below can read it

insert into public.admins (user_id) select id from auth.users where email = 'tjong.willem@gmail.com' on conflict do nothing;

-- Earlier versions had a sync-request mechanism; it is no longer needed.
drop function if exists public.admin_request_sync();
drop table if exists public.app_config;

create or replace function public.admin_stats() returns json
language plpgsql security definer set search_path = public, auth as $$
begin
  if not exists (select 1 from public.admins where user_id = auth.uid()) then raise exception 'not allowed'; end if;
  return json_build_object(
    'users', (select count(*) from auth.users),
    'scans', coalesce((select sum(scans) from public.scan_counts), 0),
    'accounts_with_scans', (select count(*) from public.scan_counts)
  );
end;
$$;

revoke all on function public.admin_stats() from public, anon;
grant execute on function public.admin_stats() to authenticated;
