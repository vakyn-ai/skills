#!/usr/bin/env sh
# AFTER: the same call to the person's own open-server. Base URL, key and model come from the
# environment, so switching back is a config change:
#   VAKYN_BASE_URL=http://127.0.0.1:8080  (server root, no /v1)
#   VAKYN_API_KEY=vk_...                  (from `vakyn keys create`; never in the script)
#   VAKYN_MODEL=jev-latest                (or the name from GET /v1/models)
# Usage: sh http_after.sh [request.json]   (default: bike-desk.request.json next to this script)
set -eu
BASE="${VAKYN_BASE_URL:-http://127.0.0.1:8080}"
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
