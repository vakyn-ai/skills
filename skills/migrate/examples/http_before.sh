#!/usr/bin/env sh
# BEFORE: raw HTTP to the hosted service. URL and model are fixed in the script.
curl -sS https://api.typesafe.ai/v1/systemone \
  -H "Authorization: Bearer $TYPESAFE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{"model": "jev-1.13.0",
 "state": {"message": "Flat tire on rental 4471, can you swap the bike?"},
 "questions": {"refund": {"type": "noul", "instructions": "Does state.message ask for money back?"}}}
JSON
