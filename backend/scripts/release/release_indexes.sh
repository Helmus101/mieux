#!/bin/bash
# Rebuild the Mieux type index and the alternatives index locally, ship them to Fly and swap them in.
# Run after changing the taxonomy rules, then deploy the code:  cd backend && scripts/release/release_indexes.sh && flyctl deploy --remote-only
# Needs flyctl logged in, the local off_local.db and op_local.db, and ~25 minutes. Nothing is swapped unless every build step succeeded.
set -euo pipefail
cd "$(dirname "$0")/../.."
APP=${FLY_APP:-mieux-api}
PY=${PY:-.venv/bin/python3.9}
FLY=${FLYCTL:-flyctl}
TMP=$(mktemp -d)
remote() { B=$(base64 < "$1" | tr -d '\n'); $FLY ssh console -a "$APP" -C "python -c \"import base64;exec(base64.b64decode('$B'))\""; }

echo "== 1/5 type index (about 18 min)"
$PY -m scripts.build_taxonomy_index --workers "${WORKERS:-7}"
$PY - "$TMP/taxo_index.db" <<'PYE'
import sqlite3, sys
d = sqlite3.connect(sys.argv[1]); d.execute("attach 'off_local.db' as o")
for t in ("off_tax", "off_taxo"):
    d.execute(d.execute("select sql from o.sqlite_master where name=?", (t,)).fetchone()[0])
    d.execute(f"insert into main.{t} select * from o.{t}")
d.commit()
assert d.execute("select count(*) from off_taxo").fetchone()[0] > 1000000
PYE
echo "== 2/5 alternatives index (about 7 min)"
$PY scripts/build_alt_index.py > "$TMP/alt.log" 2>&1 || { tail -20 "$TMP/alt.log"; exit 1; }
echo "== 3/5 upload"
$FLY ssh console -a "$APP" -C "rm -f /data/taxo_index.db /data/alt_index.db.new"
printf 'put %s /data/taxo_index.db\nput alt_index.db /data/alt_index.db.new\n' "$TMP/taxo_index.db" | $FLY ssh sftp shell -a "$APP"
echo "== 4/5 swap the type index"
remote scripts/release/remote_apply_taxo.py
echo "== 5/5 swap the alternatives index (previous one kept as /data/alt_index.db.prev-<time>)"
remote scripts/release/remote_swap_alt.py
rm -rf "$TMP"
echo "done. Deploy the code now if it changed."
