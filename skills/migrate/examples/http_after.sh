#!/usr/bin/env sh
# AFTER: the same call to VAKYN Cloud. Base URL, key and model come from the environment, so
# switching back (or to your own open-server) is a config change:
#   VAKYN_BASE_URL=https://api.vakyn.com  (root, no /v1; or your own server's URL)
#   VAKYN_API_KEY=vk_...                  (from vakyn.com/console/keys; never in the script)
#   VAKYN_MODEL=jev-latest                (works on both; on VAKYN Cloud also vakyn-fast)
# Usage: sh http_after.sh [request.json]   (default: bike-desk.request.json next to this script)
set -eu
BASE="${VAKYN_BASE_URL:-https://api.vakyn.com}"
MODEL="${VAKYN_MODEL:-jev-latest}"
BODY="${1:-$(dirname "$0")/bike-desk.request.json}"
: "${VAKYN_API_KEY:?set VAKYN_API_KEY}"

# Put the configured model into the body, then send. -D keeps the response headers so the
# x-typesafe-request-id can be logged.
python3 -c 'import json,sys; b=json.load(open(sys.argv[1])); b["model"]=sys.argv[2]; print(json.dumps(b))' "$BODY" "$MODEL" |
  curl -sS --fail-with-body -D /dev/stderr "$BASE/v1/systemone" \
    -H "Authorization: Bearer $VAKYN_API_KEY" \
    -H "Content-Type: application/json" \
    --data-binary @-
echo
