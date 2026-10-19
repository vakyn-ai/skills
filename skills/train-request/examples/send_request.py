"""Send a training request to VAKYN, after the person has read it and said yes; or check its status.

Usage:
    python3 send_request.py check training-request.json      # validate only, sends nothing
    python3 send_request.py show  training-request.json      # print exactly what would be sent
    python3 send_request.py send  training-request.json --yes  # send; --yes means the person agreed
    python3 send_request.py status [tr_...]                   # your organization's requests, or one

training-request.json follows the contract of POST /v1/training-requests (references/api.md). The key
comes from VAKYN_API_KEY (loaded from ~/.config/vakyn/env); the host from VAKYN_BASE_URL, default
https://api.vakyn.com. Sending is free: no balance is needed and nothing is charged.

When there is no key, or the API is not there (404, no connection), it says so and points to the
fallback: paste vakyn-proposal.md into https://vakyn.com/contact. Standard library only.
"""

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

CONTACT = "https://vakyn.com/contact"
TYPES = {"noul", "choice", "score"}
FIELDS = {
    "": {"schema_version", "title", "decision", "runs_on", "model", "questions", "examples", "results",
         "losing_cells", "needs", "can_share", "contact", "proposal_markdown", "client"},
    "runs_on": {"where", "region"},
    "questions[]": {"name", "type", "instructions", "options", "state"},
    "examples[]": {"input", "answer", "made_up", "question"},
    "results[]": {"question", "set", "stage", "cases", "right", "metric", "value", "source"},
    "losing_cells[]": {"question", "kind", "count", "of", "note"},
    "needs": {"target", "volume", "latency", "value", "constraints"},
    "can_share": {"labeled_cases", "labeled_by", "terms"},
    "contact": {"email", "name", "company"},
    "client": {"skill", "skills_version"},
}
CAPS = {"title": 200, "decision": 2000, "proposal_markdown": 20000}
MAX_ITEMS = {"questions": 20, "examples": 50, "results": 100, "losing_cells": 100}
MAX_BYTES = 128 * 1024


def validate(body):
    """The API's rules, checked before anything is sent. Returns a list of (path, message)."""
    errs = []
    if not isinstance(body, dict):
        return [("", "the request must be a JSON object")]

    def strict(obj, key, path):
        if not isinstance(obj, dict):
            errs.append((path, "must be an object"))
            return
        for k in sorted(set(obj) - FIELDS[key]):
            errs.append((f"{path}.{k}" if path else k, "unknown field (the API is strict at every level)"))

    strict(body, "", "")
    if body.get("schema_version") != 1:
        errs.append(("schema_version", "must be 1"))
    for k in ("title", "decision"):
        if not isinstance(body.get(k), str) or not body[k].strip():
            errs.append((k, "required"))
    for k, cap in CAPS.items():
        if isinstance(body.get(k), str) and len(body[k]) > cap:
            errs.append((k, f"{len(body[k])} characters; at most {cap}"))
    for k in ("runs_on", "needs", "can_share", "client"):
        if k in body:
            strict(body[k], k, k)
    contact = body.get("contact")
    strict(contact if contact is not None else {}, "contact", "contact")
    if not isinstance(contact, dict) or not contact.get("email"):
        errs.append(("contact.email", "required"))
    qs = body.get("questions")
    if not isinstance(qs, list) or not 1 <= len(qs) <= MAX_ITEMS["questions"]:
        errs.append(("questions", "1 to 20 questions"))
        qs = qs if isinstance(qs, list) else []
    names = []
    for i, q in enumerate(qs):
        p = f"questions[{i}]"
        strict(q, "questions[]", p)
        if not isinstance(q, dict):
            continue
        if not q.get("name"):
            errs.append((f"{p}.name", "required"))
        names.append(q.get("name"))
        if q.get("type") not in TYPES:
            errs.append((f"{p}.type", "one of noul, choice, score"))
        if "options" in q and (not isinstance(q["options"], dict) or len(q["options"]) > 255):
            errs.append((f"{p}.options", "an object of at most 255 options"))
    if len(set(names)) != len(names):
        errs.append(("questions", "question names must be unique"))
    for k in ("examples", "results", "losing_cells"):
        items = body.get(k, [])
        if not isinstance(items, list):
            errs.append((k, "must be a list"))
            continue
        if len(items) > MAX_ITEMS[k]:
            errs.append((k, f"{len(items)} items; at most {MAX_ITEMS[k]}"))
        for i, it in enumerate(items):
            strict(it, f"{k}[]", f"{k}[{i}]")
            if not isinstance(it, dict):
                continue
            if k == "examples" and it.get("made_up") is not True:
                errs.append((f"examples[{i}].made_up", "must be true: examples are invented, never real records"))
            if k == "results" and isinstance(it.get("right"), int) and isinstance(it.get("cases"), int) \
                    and it["right"] > it["cases"]:
                errs.append((f"results[{i}].right", "more than cases"))
            if k == "losing_cells" and isinstance(it.get("count"), int) and isinstance(it.get("of"), int) \
                    and it["count"] > it["of"]:
                errs.append((f"losing_cells[{i}].count", "more than of"))
    size = len(json.dumps(body).encode())
    if size > MAX_BYTES:
        errs.append(("", f"{size} bytes; at most {MAX_BYTES}"))
    return errs


def call(method, path, body=None):
    base = os.environ.get("VAKYN_BASE_URL", "https://api.vakyn.com").rstrip("/")
    key = os.environ.get("VAKYN_API_KEY", "")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{base}{path}", data=data, method=method, headers={
        "content-type": "application/json", "authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}"), r.headers
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw), e.headers
        except ValueError:
            return e.code, {"raw": raw[:300].decode(errors="replace")}, e.headers


def fallback(why):
    print(f"Not sent: {why}")
    print(f"Fallback: paste vakyn-proposal.md into {CONTACT} (topic 'Test it on your data'), or email it.")
    return 3


def explain(status, res, headers):
    if status == 401:
        return fallback("401, the key in VAKYN_API_KEY is missing, wrong or revoked")
    if status == 403:
        return fallback("403, the organization is suspended; contact VAKYN support")
    if status == 404:
        return fallback("404, this server has no training-requests API")
    if status == 413:
        print("Not sent: 413, the request is over 128 KB. Shorten proposal_markdown or the lists.")
        return 1
    if status == 422:
        print("Not sent: 422, VAKYN refused these fields:")
        for e in res.get("detail", {}).get("errors", []):
            print(f"  {e.get('path')}: {e.get('message')}")
        return 1
    if status == 429:
        print(f"Not sent: 429, more than 10 requests per organization in 24 hours. "
              f"Retry after {headers.get('retry-after', 'a while')} seconds.")
        return 1
    print(f"Not sent: HTTP {status} {res}")
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "show", "send"):
        p = sub.add_parser(name)
        p.add_argument("file")
        if name == "send":
            p.add_argument("--yes", action="store_true", help="the person read the request and agreed to send it")
    st = sub.add_parser("status")
    st.add_argument("id", nargs="?")
    a = ap.parse_args(argv)

    if a.cmd == "status":
        if not os.environ.get("VAKYN_API_KEY"):
            print("No VAKYN_API_KEY: load ~/.config/vakyn/env first.")
            return 2
        try:
            status, res, headers = call("GET", f"/v1/training-requests{'/' + a.id if a.id else ''}")
        except (urllib.error.URLError, OSError) as e:
            print(f"Cannot reach VAKYN: {e}")
            return 2
        if status != 200:
            return explain(status, res, headers)
        for r in res.get("data", [res]):
            quote = f", quote {r['quote']}" if r.get("quote") else ""
            print(f"{r['id']}  {r['status']:<11}  {r['created_at'][:10]}  {r['title']}{quote}\n  {r['url']}")
            for m in r.get("messages", []):
                print(f"  [{m['created_at'][:10]}] {m['from']}: {m['body']}")
        return 0

    body = json.loads(pathlib.Path(a.file).read_text())
    errs = validate(body)
    if errs:
        print(f"{a.file}: {len(errs)} problem(s); fix them before sending:")
        for path, msg in errs:
            print(f"  {path or '(body)'}: {msg}")
        return 1
    if a.cmd == "check":
        print(f"{a.file}: OK, {len(json.dumps(body).encode())} bytes. Nothing was sent.")
        return 0
    if a.cmd == "show":
        print(json.dumps(body, indent=2, ensure_ascii=False))
        print("\nThis is exactly what would be sent. Nothing was sent.")
        return 0
    if not a.yes:
        print("Not sent: the person must read the request (`show`) and agree first; then pass --yes.")
        return 2
    if not os.environ.get("VAKYN_API_KEY"):
        return fallback("no VAKYN_API_KEY in the environment (load ~/.config/vakyn/env)")
    try:
        status, res, headers = call("POST", "/v1/training-requests", body)
    except (urllib.error.URLError, OSError) as e:
        return fallback(f"cannot reach VAKYN ({e})")
    if status != 201:
        return explain(status, res, headers)
    print(f"Sent: {res['id']}, status {res['status']}.")
    print(f"Follow it in the console: {res['url']}")
    print("Replies from VAKYN appear there and in `python3 send_request.py status`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
