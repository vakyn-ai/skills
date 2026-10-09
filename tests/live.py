"""Send every example request to a running open-server and check the answers.

Usage: VAKYN_API_KEY=vk_... python3 tests/live.py
Base URL from VAKYN_BASE_URL (default http://127.0.0.1:8080). Exits 0 and prints SKIP when
no server answers, so it is safe in CI without a server.
"""

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = os.environ.get("VAKYN_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
KEY = os.environ.get("VAKYN_API_KEY", "")


def post(body):
    req = urllib.request.Request(
        f"{BASE}/v1/systemone",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json", "authorization": f"Bearer {KEY}"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def answer_ok(q, a):
    if a.get("type") != q["type"]:
        return "wrong answer type"
    if q["type"] == "noul":
        return None if 0 <= a.get("noul", -1) <= 1 else "noul not a probability"
    if q["type"] == "choice":
        if a.get("choice") not in q["criteria"]:
            return f"choice {a.get('choice')!r} is not an offered option"
        if set(a.get("probabilities", {})) - set(q["criteria"]):
            return "probabilities name options that were not offered"
        return None
    levels = len(q["criteria"])
    return None if 0 <= a.get("score", -1) <= levels - 1 else "score out of range"


def main():
    try:
        urllib.request.urlopen(f"{BASE}/v1/models", timeout=5)
    except urllib.error.HTTPError:
        pass  # 401 still means a server is there
    except (urllib.error.URLError, OSError):
        print(f"SKIP: no server at {BASE}")
        return 0
    if not KEY:
        print("FAIL: set VAKYN_API_KEY")
        return 1

    files = sorted(ROOT.glob("skills/**/*.request.json"))
    failed = 0
    for f in files:
        rel = f.relative_to(ROOT)
        body = json.loads(f.read_text())
        try:
            res = post(body)
        except urllib.error.HTTPError as e:
            print(f"FAIL {rel}: HTTP {e.code} {e.read()[:200]!r}")
            failed += 1
            continue
        problems = []
        for qid, q in body["questions"].items():
            a = res.get("answers", {}).get(qid)
            p = "missing answer" if a is None else answer_ok(q, a)
            if p:
                problems.append(f"{qid}: {p}")
        if problems:
            failed += 1
            print(f"FAIL {rel}: " + "; ".join(problems))
        else:
            short = {k: v.get("choice", v.get("noul", v.get("score"))) for k, v in res["answers"].items()}
            print(f"ok   {rel} {short}")
    print(f"{len(files) - failed}/{len(files)} example requests answered")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
