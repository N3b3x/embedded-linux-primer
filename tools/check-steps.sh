#!/usr/bin/env bash
# Resolve every walkthrough step against the real layout, in headless Chrome.
# Needs a built site (python3 tools/build-site.py) and Google Chrome or Chromium on this machine.
# Usage: tools/check-steps.sh
set -euo pipefail
TOP="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE="$TOP/build/site-out"
[ -d "$SITE" ] || { echo "build the site first: python3 tools/build-site.py" >&2; exit 2; }
CHROME="${CHROME:-}"
for c in "$CHROME" "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" google-chrome chromium chromium-browser; do
  [ -n "$c" ] && command -v "$c" >/dev/null 2>&1 && { CHROME="$c"; break; } || [ -x "$c" ] && { CHROME="$c"; break; }
done
[ -n "$CHROME" ] || { echo "no Chrome/Chromium found (set CHROME=...)" >&2; exit 2; }
PORT=8799
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$SITE" >/dev/null 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null || true' EXIT
sleep 1
OUT="$("$CHROME" --headless=new --disable-gpu --user-data-dir="$(mktemp -d)" --window-size=1440,900 \
  --virtual-time-budget=90000 --dump-dom "http://127.0.0.1:$PORT/docs/index.html?dvcheck=1" 2>/dev/null \
  | grep -o '<pre id="dv-check-result">[^<]*</pre>' | sed 's/<[^>]*>//g' | sed 's/&quot;/"/g')"
[ -n "$OUT" ] || { echo "the check did not finish (no result in the page)" >&2; exit 2; }
python3 - "$OUT" <<'PY'
import json, sys
r = json.loads(sys.argv[1])
for p in r["problems"]:
    print("%s step %d: anchor not found: %s" % (p["diagram"], p["step"], ", ".join(p["missing"])))
import os
if os.environ.get("STATS"):
    for t in r["stats"]:
        flag = "  <-- large" if t["pct"] > 40 else ("  <-- tiny" if t["pct"] < 0.4 and t["n"] else "")
        print("%-40s step %2d  %5.1f%%%s" % (t["diagram"], t["step"], t["pct"], flag))
print("resolved the walkthroughs of %d diagram(s), %d problem(s)" % (r["checked"], len(r["problems"])))
sys.exit(1 if r["problems"] else 0)
PY
