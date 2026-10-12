#!/bin/sh
# Send first-call.request.json to your server. Needs VAKYN_API_KEY in the environment.
curl -sS "${VAKYN_BASE_URL:-http://127.0.0.1:8080}/v1/systemone" \
  -H "Authorization: Bearer $VAKYN_API_KEY" \
  -H "Content-Type: application/json" \
  --data @"$(dirname "$0")/first-call.request.json"
