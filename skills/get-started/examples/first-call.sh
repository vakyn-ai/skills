#!/bin/sh
# Send first-call.request.json to VAKYN Cloud, or to your own server with VAKYN_BASE_URL set.
# Needs VAKYN_API_KEY in the environment.
curl -sS "${VAKYN_BASE_URL:-https://api.vakyn.com}/v1/systemone" \
  -H "Authorization: Bearer $VAKYN_API_KEY" \
  -H "Content-Type: application/json" \
  --data @"$(dirname "$0")/first-call.request.json"
