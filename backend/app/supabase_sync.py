"""Optional copy of newsletter addresses into Supabase (table `subscribers`), on top of the local database.

Active only when SUPABASE_URL and SUPABASE_SERVICE_KEY are set (the service key stays on the server, never in the web app).
Best effort: a Supabase outage never breaks the sign-up, the address is already saved locally.
Table (run once in the Supabase SQL editor):

    create table if not exists subscribers (
      email text primary key, lang text, country text, consent_at timestamptz default now());
    alter table subscribers enable row level security;   -- no policies: only the service key can read or write
"""
import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Optional

log = logging.getLogger("app.supabase")


def enabled() -> bool:
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY"))


def _call(method, path, body=None, prefer=None, transport=None):
    base = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_KEY"]
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
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
        _call("POST", "subscribers?on_conflict=email", {"email": email, "lang": lang, "country": country},
              prefer="resolution=ignore-duplicates,return=minimal", transport=transport)
        return True
    except Exception as e:  # noqa: BLE001 - never let a third party break the sign-up
        log.warning("supabase subscriber sync failed: %s", type(e).__name__)
        return False


def delete_subscriber(email: str, transport=None) -> bool:
    if not enabled():
        return False
    try:
        _call("DELETE", "subscribers?email=eq." + urllib.parse.quote(email, safe=""), transport=transport)
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("supabase subscriber delete failed: %s", type(e).__name__)
        return False
