"""Live check for the optimize loop on public datasets: TweetEval irony (noul) and TREC (choice, bare codes).

Usage: VAKYN_API_KEY=vk_... [VAKYN_BASE_URL=...] [MODEL=vakyn-fast] [N=300] [DATASETS=irony,trec]
       python3 tests/live_optimize.py
For each dataset, runs optimize.py start / try / finish with a fixed rewrite written from misses
(tests/fixtures/<name>.v2.request.json) on the first N rows of the test split, and fails if the
reserved score after optimizing is below the starting score. About N x 2 requests per dataset;
pointing it at https://api.vakyn.com spends real balance. Exits 0 and prints SKIP when no server answers.
"""

import contextlib
import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "optimize" / "examples"))
import optimize  # noqa: E402

BASE = os.environ.get("VAKYN_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
KEY = os.environ.get("VAKYN_API_KEY", "")
MODEL = os.environ.get("MODEL", "vakyn-fast")
N = int(os.environ.get("N", "300"))
ROWS = "https://datasets-server.huggingface.co/rows?dataset={}&config={}&split=test"
DATASETS = {
    # name: (dataset, config, question type, row -> (state, label), rule for the rewrite)
    "irony": ("cardiffnlp/tweet_eval", "irony", "noul",
              lambda r: ({"tweet": r["text"]}, bool(r["label"])),
              "false negative: a hashtag such as #not or #sarcasm, or praise for something plainly bad, counts as ironic"),
    "trec": ("SetFit/TREC-QC", "default", "choice",
             lambda r: ({"question": r["text"]}, r["label_coarse_original"]),
             "bare codes: describe each answer type, and classify by the expected answer, not the topic"),
}


def rows(name, n):
    dataset, config, _, convert, _ = DATASETS[name]
    out = []
    while len(out) < n:
        url = ROWS.format(dataset, config) + f"&offset={len(out)}&length={min(100, n - len(out))}"
        with urllib.request.urlopen(url, timeout=60) as r:
            got = json.loads(r.read())["rows"]
        if not got:
            break
        for x in got:
            state, label = convert(x["row"])
            out.append({"id": f"{name}-test-{x['row_idx']}", "state": state, "label": label})
    return out


def run(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = optimize.main(list(args))
    print(out.getvalue())
    return code, out.getvalue()


def main():
    try:
        urllib.request.urlopen(f"{BASE}/v1/models", timeout=5)
    except urllib.error.HTTPError:
        pass
    except (urllib.error.URLError, OSError):
        print(f"SKIP: no server at {BASE}")
        return 0
    if not KEY:
        print("FAIL: set VAKYN_API_KEY")
        return 1
    os.environ["TYPESAFE_BASE_URL"], os.environ["TYPESAFE_API_KEY"] = BASE, KEY

    failed = 0
    for name in os.environ.get("DATASETS", "irony,trec").split(","):
        failed += check_dataset(name)
    return 1 if failed else 0


def check_dataset(name):
    qtype, rule = DATASETS[name][2], DATASETS[name][4]
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"optimize-live-{name}-"))
    cases = tmp / "cases.jsonl"
    cases.write_text("".join(json.dumps(c) + "\n" for c in rows(name, N)))
    rundir = str(tmp / "run")
    fx = ROOT / "tests" / "fixtures"
    code, _ = run("start", "--request", str(fx / f"{name}.v1.request.json"), "--cases", str(cases),
                  "--model", MODEL, "--rounds", "1", "--yes", "--run", rundir)
    if code:
        return 1
    run("try", "--candidate", str(fx / f"{name}.v2.request.json"), "--run", rundir, "--rule", rule)
    run("finish", "--run", rundir)
    state = json.loads((tmp / "run" / "run.json").read_text())
    start, best = state["reserved"]["start"], state["reserved"]["best"]
    print(f"{name} on {MODEL}, {N} rows. Reserved: start {optimize.show(qtype, start)}; "
          f"best {optimize.show(qtype, best)}. Run folder: {tmp}")
    if optimize.key_of(qtype, best, "accuracy") < optimize.key_of(qtype, start, "accuracy"):
        print(f"FAIL {name}: the reserved score after optimizing is below the starting score")
        return 1
    shutil.rmtree(tmp)
    print(f"ok {name}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
