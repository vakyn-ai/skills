"""Offline tests for skills/optimize/examples/optimize.py against a fake VAKYN endpoint.

The fake returns fixed answers per wording, so the loop's rules can be checked without a server:
the split is stable, a candidate that scores lower on dev is discarded, reserved cases are sent
only by finish, option keys never change, and the call estimate comes before the first call.
"""

import contextlib
import http.server
import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "skills" / "optimize" / "examples"
sys.path.insert(0, str(EXAMPLES))
sys.path.insert(0, str(ROOT / "skills" / "check" / "examples"))

import optimize  # noqa: E402
import promote  # noqa: E402

CASES = [json.loads(line) for line in (EXAMPLES / "cases.sample.jsonl").open()]
DEV = {c["id"] for c in CASES if not optimize.reserved(c["id"], 0.3)}
RESERVED = {c["id"] for c in CASES if optimize.reserved(c["id"], 0.3)}
LABEL = {c["text"]: c["label"] for c in CASES}
ID = {c["text"]: c["id"] for c in CASES}


class Fake:
    """A fake /v1/systemone. `wrong[wording_hash]` is the set of case ids that wording gets wrong."""

    def __init__(self):
        self.wrong, self.events, self.sent = {}, [], []
        fake = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["content-length"])))
                (name, q), = body["questions"].items()
                text = body["state"]["message"]
                cid = ID[text]
                fake.sent.append(cid)
                fake.events.append("call")
                wrong = cid in fake.wrong.get(optimize.wording_hash(q), set())
                pick = LABEL[text] if not wrong else ("OTH" if LABEL[text] != "OTH" else "ACC")
                probs = {k: (0.9 if k == pick else 0.1 / (len(q["criteria"]) - 1)) for k in q["criteria"]}
                out = {"answers": {name: {"type": "choice", "choice": pick, "confidence": 0.9, "probabilities": probs}}}
                data = json.dumps(out).encode()
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class Tee(io.StringIO):
    def __init__(self, events):
        super().__init__()
        self.events = events

    def write(self, s):
        if s.strip():
            self.events.append(s)
        return super().write(s)


def question(path):
    return optimize.load_request(path)[2]


class OptimizeLoop(unittest.TestCase):
    def setUp(self):
        self.fake = Fake()
        self.dir = pathlib.Path(tempfile.mkdtemp())
        self.run_dir = self.dir / "run"
        shutil.copy(EXAMPLES / "intent.v1.request.json", self.dir / "v1.json")
        self.env = {k: os.environ.get(k) for k in ("TYPESAFE_BASE_URL", "TYPESAFE_API_KEY")}
        os.environ["TYPESAFE_BASE_URL"] = self.fake.url
        os.environ["TYPESAFE_API_KEY"] = "vk_test"
        dev = sorted(DEV)
        self.fake.wrong[optimize.wording_hash(question(self.dir / "v1.json"))] = set(dev[:10]) | set(sorted(RESERVED)[:4])

    def tearDown(self):
        self.fake.close()
        shutil.rmtree(self.dir)
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def run_cli(self, *args):
        out = Tee(self.fake.events)
        with contextlib.redirect_stdout(out):
            code = optimize.main([*args, "--run", str(self.run_dir)])
        return code, out.getvalue()

    def start(self, *extra):
        return self.run_cli("start", "--request", str(self.dir / "v1.json"),
                            "--cases", str(EXAMPLES / "cases.sample.jsonl"), *extra)

    def candidate(self, name, wrong, edit=None):
        req = json.loads((self.dir / "v1.json").read_text())
        q = req["questions"]["intent"]
        q["criteria"] = {k: f"{k}: described {name}" for k in q["criteria"]}
        if edit:
            edit(req)
        path = self.dir / name
        path.write_text(json.dumps(req))
        self.fake.wrong[optimize.wording_hash(req["questions"].get("intent", q))] = wrong
        return path

    def test_split_is_stable_and_matches_check(self):
        ids = [f"case-{i}" for i in range(500)]
        first = [optimize.reserved(i, 0.3) for i in ids]
        self.assertEqual(first, [optimize.reserved(i, 0.3) for i in ids])
        self.assertEqual(first, [promote.reserved(i, 0.3) for i in ids])
        self.assertTrue(0.2 < sum(first) / len(first) < 0.4)

    def test_estimate_printed_before_first_call(self):
        code, out = self.start("--yes")
        self.assertEqual(code, 0)
        estimate = next(i for i, e in enumerate(self.fake.events) if "Estimate: up to" in e)
        self.assertLess(estimate, self.fake.events.index("call"))

    def test_estimate_above_limit_needs_yes(self):
        code, out = self.start("--confirm-above", "10")
        self.assertEqual(code, 3)
        self.assertIn("Estimate: up to", out)
        self.assertEqual(self.fake.sent, [])

    def test_rounds_never_send_reserved_cases(self):
        self.start("--yes")
        dev = sorted(DEV)
        self.run_cli("try", "--candidate", str(self.candidate("v2.json", set(dev[:4]))))
        self.run_cli("try", "--candidate", str(self.candidate("v3.json", set(dev[:2]))))
        self.assertTrue(self.fake.sent)
        self.assertEqual(set(self.fake.sent) & RESERVED, set())
        self.run_cli("finish")
        self.assertEqual(set(self.fake.sent) & RESERVED, RESERVED)

    def test_worse_candidate_is_discarded(self):
        self.start("--yes")
        dev = sorted(DEV)
        code, out = self.run_cli("try", "--candidate", str(self.candidate("v2.json", set(dev[:20]))))
        self.assertIn("Discard the candidate", out)
        run = json.loads((self.run_dir / "run.json").read_text())
        self.assertEqual(run["best"]["file"], str(self.dir / "v1.json"))
        code, out = self.run_cli("try", "--candidate", str(self.candidate("v3.json", set(dev[:3]))),
                                 "--rule", "CRD -> OTH: describe every code")
        self.assertIn("Keep the candidate", out)
        run = json.loads((self.run_dir / "run.json").read_text())
        self.assertEqual(run["best"]["file"], str(self.dir / "v3.json"))
        self.assertEqual(run["best"]["rules"], ["CRD -> OTH: describe every code"])

    def test_tie_keeps_the_shorter_wording(self):
        self.start("--yes")
        same = self.fake.wrong[optimize.wording_hash(question(self.dir / "v1.json"))] & DEV
        longer = self.candidate("v2.json", same)
        code, out = self.run_cli("try", "--candidate", str(longer))
        self.assertIn("Discard the candidate", out)

    def test_option_keys_and_name_never_change(self):
        self.start("--yes")
        sent = len(self.fake.sent)

        def rename_key(req):
            c = req["questions"]["intent"]["criteria"]
            c["CARD"] = c.pop("CRD")

        def rename_question(req):
            req["questions"]["topic"] = req["questions"].pop("intent")

        for name, edit in (("keys.json", rename_key), ("name.json", rename_question)):
            with self.subTest(edit=name):
                code, out = self.run_cli("try", "--candidate", str(self.candidate(name, set(), edit)))
                self.assertEqual(code, 2)
                self.assertIn("Stopped:", out)
        self.assertEqual(len(self.fake.sent), sent)

    def test_candidate_never_overwrites_current(self):
        self.start("--yes")
        code, out = self.run_cli("try", "--candidate", str(self.dir / "v1.json"))
        self.assertEqual(code, 2)
        self.assertIn("new versioned file", out)

    def test_promote_only_when_not_worse_on_reserved(self):
        self.start("--yes")
        dev, res = sorted(DEV), sorted(RESERVED)
        # better on dev (2 wrong instead of 10), worse on reserved (8 wrong instead of 4)
        self.run_cli("try", "--candidate", str(self.candidate("v2.json", set(dev[:2]) | set(res[:8]))))
        log = self.dir / "promotions.jsonl"
        code, out = self.run_cli("finish", "--log", str(log))
        self.assertEqual(code, 1)
        self.assertIn("Verdict: KEEP", out)
        self.assertIn("worse on reserved", out)
        entry = json.loads(log.read_text())
        self.assertEqual(entry["verdict"], "keep")
        for field in ("ts", "current", "candidate", "dev", "reserved", "live", "calls"):
            self.assertIn(field, entry)
        self.assertTrue((self.run_dir / "report.md").exists())

    def test_promote_and_report(self):
        self.start("--yes")
        dev, res = sorted(DEV), sorted(RESERVED)
        self.run_cli("try", "--candidate", str(self.candidate("v2.json", set(dev[:2]) | set(res[:2]))),
                     "--rule", "CRD -> OTH: describe every code")
        code, out = self.run_cli("finish")
        self.assertEqual(code, 0)
        self.assertIn("Verdict: PROMOTE", out)
        report = (self.run_dir / "report.md").read_text()
        self.assertIn("CRD -> OTH: describe every code", report)
        self.assertIn("Model calls used:", report)
        code, out = self.run_cli("finish")
        self.assertEqual(code, 2, "the reserved set is scored once per run")

    def test_no_key_no_scores(self):
        os.environ.pop("TYPESAFE_API_KEY")
        code, out = self.start("--yes")
        self.assertEqual(code, 2)
        self.assertIn("TYPESAFE_API_KEY is not set", out)
        self.assertNotIn("accuracy", out)
        self.assertEqual(self.fake.sent, [])

    def test_stored_answers_are_not_asked_again(self):
        self.start("--yes")
        sent = len(self.fake.sent)
        self.start("--yes", "--restart")
        self.assertEqual(len(self.fake.sent), sent)

    def test_few_cases_warns(self):
        few = self.dir / "few.jsonl"
        few.write_text("".join(json.dumps(c) + "\n" for c in CASES[:30]))
        code, out = self.run_cli("start", "--request", str(self.dir / "v1.json"), "--cases", str(few), "--yes")
        self.assertIn("label at least 20 more", out)


class SampleReplay(unittest.TestCase):
    def test_sample_promotes_offline_from_stored_answers(self):
        d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        run = d / "run"
        run.mkdir()
        shutil.copy(EXAMPLES / "answers.sample.jsonl", run / "answers.jsonl")
        key = os.environ.pop("TYPESAFE_API_KEY", None)
        self.addCleanup(lambda: key is None or os.environ.__setitem__("TYPESAFE_API_KEY", key))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(optimize.main(["start", "--request", str(EXAMPLES / "intent.v1.request.json"),
                                            "--cases", str(EXAMPLES / "cases.sample.jsonl"), "--rounds", "1",
                                            "--run", str(run)]), 0)
            optimize.main(["try", "--candidate", str(EXAMPLES / "intent.v2.request.json"), "--run", str(run)])
            self.assertEqual(optimize.main(["finish", "--run", str(run)]), 0)
        self.assertIn("Calls used: 0.", out.getvalue())
        self.assertIn("Verdict: PROMOTE", out.getvalue())


class Metrics(unittest.TestCase):
    def test_noul_and_score(self):
        cases = [{"id": "a", "label": True}, {"id": "b", "label": "false"}, {"id": "c", "label": True}]
        answers = {"a": {"noul": 0.9}, "b": {"noul": 0.7}, "c": {"noul": 0.4}}
        s = optimize.score("noul", cases, answers, 0.5)
        self.assertEqual(s["right"], 1)
        self.assertAlmostEqual(s["ap"], (1 + 2 / 3) / 2)
        groups = dict(optimize.miss_groups("noul", cases, answers, 0.5))
        self.assertEqual(len(groups["false positive (said true, label false)"]), 1)
        self.assertEqual(len(groups["false negative (said false, label true)"]), 1)
        cases = [{"id": "a", "label": 2}, {"id": "b", "label": 0}, {"id": "c", "label": 3}]
        answers = {"a": {"score": 2}, "b": {"score": 1}, "c": {"score": 1}}
        s = optimize.score("score", cases, answers, 0.5)
        self.assertEqual((s["right"], s["within_one"], s["mae"]), (1, 2 / 3, 1.0))
        groups = dict(optimize.miss_groups("score", cases, answers, 0.5))
        self.assertEqual((len(groups["too high"]), len(groups["too low"])), (1, 1))


if __name__ == "__main__":
    unittest.main()
