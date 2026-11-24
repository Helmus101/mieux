"""Optional copy of newsletter addresses into Supabase (table `subscribers`), on top of the local database.

Active only when SUPABASE_URL and a key are set: SUPABASE_PUBLISHABLE_KEY (sb_publishable_..., insert-only through the
policy below) or SUPABASE_SECRET_KEY (sb_secret_..., bypasses row-level security). The key is read by the server only. Best effort: a Supabase outage never breaks the sign-up, the
address is already saved locally.
Table (run once in the Supabase SQL editor):

    create table if not exists subscribers (
      email text primary key, lang text, country text, consent_at timestamptz default now());
    alter table subscribers enable row level security;
    -- the publishable key (role anon) may ADD a row and nothing else: it cannot read, change or delete the list
    create policy "anyone can subscribe" on subscribers for insert to anon with check (true);

Scan total: ONE row holding the total number of products scanned - no barcode, no user, no row per scan. The publishable key
cannot update rows, so it calls a function that only adds 1:

    create table if not exists scan_total (id int primary key default 1 check (id = 1), total bigint not null default 0, updated_at timestamptz default now());
    insert into scan_total (id, total) values (1, 0) on conflict (id) do nothing;
    alter table scan_total enable row level security;
    create or replace function increment_scans() returns void language sql security definer set search_path = public
      as $$ update scan_total set total = total + 1, updated_at = now() where id = 1 $$;
    revoke all on function increment_scans() from public;
    grant execute on function increment_scans() to anon;
    -- the total:  select total from scan_total;

Onboarding total: the same kind of single row, +1 each time someone presses "Get started" (no user, no device):

    create table if not exists onboarding_total (id int primary key default 1 check (id = 1), total bigint not null default 0, updated_at timestamptz default now());
    insert into onboarding_total (id, total) values (1, 0) on conflict (id) do nothing;
    alter table onboarding_total enable row level security;
    create or replace function increment_onboarding() returns void language sql security definer set search_path = public
      as $$ update onboarding_total set total = total + 1, updated_at = now() where id = 1 $$;
    revoke all on function increment_onboarding() from public;
    grant execute on function increment_onboarding() to anon;
    -- the total:  select total from onboarding_total;

Removing an address on unsubscribe needs SUPABASE_SECRET_KEY (server only); with the publishable key alone the address stays in Supabase and must be deleted from the dashboard.
"""
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

log = logging.getLogger("app.supabase")


def enabled() -> bool:
    return bool(os.environ.get("SUPABASE_URL") and _key())


def _key():
    return os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_PUBLISHABLE_KEY")


def _call(method, path, body=None, prefer=None, transport=None):
    base = os.environ["SUPABASE_URL"].rstrip("/")
    key = _key()
    # New-style keys (sb_...) are not JWTs and go in `apikey` only; a legacy JWT key also goes in Authorization.
    headers = {"apikey": key, "Content-Type": "application/json"}
    if key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {key}"
    if prefer:
        headers["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    if transport:
        return transport(method, f"{base}/rest/v1/{path}", headers, data)
    req = urllib.request.Request(f"{base}/rest/v1/{path}", data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=8) as r:
        return r.status


def push_subscriber(email: str, lang: Optional[str], country: Optional[str], transport=None) -> bool:
    if not enabled():
        return False
    try:
        # Plain insert: an "upsert" needs read rights, which the insert-only policy deliberately withholds.
        _call("POST", "subscribers", {"email": email, "lang": lang, "country": country}, prefer="return=minimal", transport=transport)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 409:   # already on the list: that is fine
            return True
        log.warning("supabase subscriber sync failed: HTTP %s", e.code)
        return False
    except Exception as e:  # noqa: BLE001 - never let a third party break the sign-up
        log.warning("supabase subscriber sync failed: %s", type(e).__name__)
        return False


def delete_subscriber(email: str, transport=None) -> bool:
    if not enabled():
        return False
    if not os.environ.get("SUPABASE_SECRET_KEY"):
        # The publishable key may not delete: Supabase would answer 204 and remove nothing, which must not read as "deleted".
        log.warning("supabase subscriber delete skipped: set SUPABASE_SECRET_KEY so unsubscribes also remove the address there")
        return False
    try:
        _call("DELETE", "subscribers?email=eq." + urllib.parse.quote(email, safe=""), transport=transport)
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("supabase subscriber delete failed: %s", type(e).__name__)
        return False


def push_scan(transport=None) -> bool:
    """Adds 1 to the single scan total in Supabase. Nothing about the product or the person is sent."""
    if not enabled():
        return False
    try:
        _call("POST", "rpc/increment_scans", {}, prefer="return=minimal", transport=transport)
        return True
    except Exception as e:  # noqa: BLE001 - best effort, never slows or breaks a scan
        log.warning("supabase scan count failed: %s", type(e).__name__)
        return False


def push_onboarding(transport=None) -> bool:
    """Adds 1 to the single "Get started" total in Supabase. Nothing about the person is sent."""
    if not enabled():
        return False
    try:
        _call("POST", "rpc/increment_onboarding", {}, prefer="return=minimal", transport=transport)
        return True
    except Exception as e:  # noqa: BLE001 - best effort, never breaks onboarding
        log.warning("supabase onboarding count failed: %s", type(e).__name__)
        return False
