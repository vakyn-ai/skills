"""Check the requests skills wrote during `claude plugin eval`.

The eval sandbox has no network, so evals check behavior and the agent saves its requests as JSON
files. This script reads the run result (`--json` output, run with `--keep-temp`), pulls every JSON
request the agent wrote out of each run's trace, runs the pre-send checklist on it and sends it to
a real server. Then it removes the kept sandboxes.

Usage: python3 tests/eval_live.py evals/last.json
Needs VAKYN_API_KEY; VAKYN_BASE_URL defaults to http://127.0.0.1:8080.
"""

import json
import os
import pathlib
import shutil
import stat
import sys
import urllib.error

from checklist import check
from live import answer_ok, post


def written_requests(trace_path):
    """Yield (file_name, request) for every Write of a JSON request in a run trace."""
    for line in open(trace_path):
        event = json.loads(line)
        if event.get("type") != "assistant":
            continue
        for block in event["message"].get("content", []):
            if block.get("type") != "tool_use" or block.get("name") != "Write":
                continue
            path = block["input"].get("file_path", "")
            if not path.endswith(".json"):
                continue
            try:
                body = json.loads(block["input"].get("content", ""))
            except json.JSONDecodeError:
                continue
            if isinstance(body, dict) and "questions" in body:
                yield pathlib.Path(path).name, body


def kept_dir(trace_path):
    # <kept>/out/trace.jsonl → <kept>, only for the eval runner's own temp dirs
    d = pathlib.Path(trace_path).parent.parent
    return d if d.name.startswith("claude-eval-") and str(d).startswith("/tmp/") else None


def remove_kept(d):
    # The runner leaves kept sandboxes read-only (some parts mode 000); open them, then delete.
    os.chmod(d, stat.S_IRWXU)
    for root, dirs, _ in os.walk(d):  # top-down: each dir is opened before the walk enters it
        for name in dirs:
            p = os.path.join(root, name)
            os.chmod(p, os.stat(p).st_mode | stat.S_IRWXU)
    shutil.rmtree(d, ignore_errors=True)


def main(result_file):
    result = json.load(open(result_file))
    checked = failed = 0
    kept = set()
    for case in result["cases"]:
        name = case.get("name") or case.get("id")
        for run in case.get("arms", {}).get("with", []):
            trace = run.get("tracePath")
            if not trace or not os.path.exists(trace):
                continue
            if kept_dir(trace):
                kept.add(kept_dir(trace))
            for fname, body in written_requests(trace):
                checked += 1
                errors, warnings = check(body)
                problems = list(errors)
                if not errors:
                    try:
                        res = post(body)
                        for qid, q in body["questions"].items():
                            a = res.get("answers", {}).get(qid)
                            p = "missing answer" if a is None else answer_ok(q, a)
                            if p:
                                problems.append(f"{qid}: {p}")
                    except urllib.error.HTTPError as e:
                        problems.append(f"HTTP {e.code} {e.read()[:200]!r}")
                    except (urllib.error.URLError, OSError) as e:
                        problems.append(f"server unreachable: {e}")
                if problems:
                    failed += 1
                    print(f"FAIL {name} / {fname}: " + "; ".join(problems))
                else:
                    note = f" ({len(warnings)} checklist warnings)" if warnings else ""
                    print(f"ok   {name} / {fname}{note}")
    for d in kept:
        remove_kept(d)
    print(f"{checked - failed}/{checked} requests written by skills passed the checklist and got answers")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "evals/last.json"))
