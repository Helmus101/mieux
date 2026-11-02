-- Run once in Supabase: SQL Editor > New query > paste > Run.
-- The only thing stored per account: how many scans. Users can read their own number and cannot write it directly.

create table if not exists public.scan_counts (
  user_id uuid primary key references auth.users (id) on delete cascade,
  scans integer not null default 0 check (scans >= 0),
  updated_at timestamptz not null default now()
);

alter table public.scan_counts enable row level security;

drop policy if exists "read own scan count" on public.scan_counts;
create policy "read own scan count" on public.scan_counts
  for select to authenticated using (user_id = auth.uid());

-- No insert/update/delete policies on purpose: the count only changes through this function.
create or replace function public.increment_scans() returns integer
language sql security definer set search_path = public as $$
  insert into public.scan_counts (user_id, scans) values (auth.uid(), 1)
  on conflict (user_id) do update set scans = public.scan_counts.scans + 1, updated_at = now()
  returning scans;
$$;

revoke all on function public.increment_scans() from public, anon;
grant execute on function public.increment_scans() to authenticated;

-- To see everyone's totals (dashboard / SQL editor): select u.email, c.scans from public.scan_counts c join auth.users u on u.id = c.user_id order by c.scans desc;
