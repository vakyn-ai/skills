"""Offline tests for skills/train-request/examples/send_request.py against a fake training-requests API.

Checks the contract rules before sending (strict fields at every level, made_up examples, counts),
that nothing is sent without --yes or a key, and how each answer of the API is reported.
"""

import contextlib
import copy
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
EXAMPLES = ROOT / "skills" / "train-request" / "examples"
sys.path.insert(0, str(EXAMPLES))

import send_request  # noqa: E402

SAMPLE = json.loads((EXAMPLES / "training-request.sample.json").read_text())


class Fake:
    def __init__(self):
        self.calls, self.reply = [], (201, {"id": "tr_1", "status": "received",
                                            "url": "https://vakyn.com/console/training/tr_1"}, {})
        fake = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def handle_one(self, method):
                n = int(self.headers.get("content-length") or 0)
                body = json.loads(self.rfile.read(n)) if n else None
                fake.calls.append((method, self.path, self.headers.get("authorization"), body))
                status, data, headers = fake.reply
                raw = json.dumps(data).encode()
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                self.handle_one("POST")

            def do_GET(self):
                self.handle_one("GET")

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class Validate(unittest.TestCase):
    def test_sample_is_valid(self):
        self.assertEqual(send_request.validate(SAMPLE), [])

    def paths(self, body):
        return {p for p, _ in send_request.validate(body)}

    def test_contract_rules(self):
        cases = [
            (lambda b: b.update(extra=1), "extra"),
            (lambda b: b["questions"][0].update(colour="red"), "questions[0].colour"),
            (lambda b: b["contact"].update(phone="1"), "contact.phone"),
            (lambda b: b["examples"][0].update(made_up=False), "examples[0].made_up"),
            (lambda b: b["examples"][1].pop("made_up"), "examples[1].made_up"),
            (lambda b: b["results"][0].update(right=21), "results[0].right"),
            (lambda b: b["losing_cells"][0].update(count=50), "losing_cells[0].count"),
            (lambda b: b["questions"].append(dict(b["questions"][0])), "questions"),
            (lambda b: b["questions"][0].update(type="rank"), "questions[0].type"),
            (lambda b: b.update(schema_version=2), "schema_version"),
            (lambda b: b["contact"].pop("email"), "contact.email"),
            (lambda b: b.update(title="x" * 201), "title"),
            (lambda b: b.pop("decision"), "decision"),
        ]
        for edit, path in cases:
            with self.subTest(path=path):
                body = copy.deepcopy(SAMPLE)
                edit(body)
                self.assertIn(path, self.paths(body))


class Send(unittest.TestCase):
    def setUp(self):
        self.fake = Fake()
        self.dir = pathlib.Path(tempfile.mkdtemp())
        self.file = self.dir / "training-request.json"
        self.file.write_text(json.dumps(SAMPLE))
        self.env = {k: os.environ.get(k) for k in ("VAKYN_BASE_URL", "VAKYN_API_KEY")}
        os.environ["VAKYN_BASE_URL"] = self.fake.url
        os.environ["VAKYN_API_KEY"] = "vk_test"

    def tearDown(self):
        self.fake.close()
        shutil.rmtree(self.dir)
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = send_request.main(list(args))
        return code, out.getvalue()

    def test_nothing_sent_without_yes(self):
        for cmd in (["check", str(self.file)], ["show", str(self.file)], ["send", str(self.file)]):
            self.run_cli(*cmd)
        self.assertEqual(self.fake.calls, [])

    def test_nothing_sent_when_invalid(self):
        bad = copy.deepcopy(SAMPLE)
        bad["examples"][0]["made_up"] = False
        self.file.write_text(json.dumps(bad))
        code, out = self.run_cli("send", str(self.file), "--yes")
        self.assertEqual(code, 1)
        self.assertIn("examples[0].made_up", out)
        self.assertEqual(self.fake.calls, [])

    def test_no_key_falls_back(self):
        os.environ.pop("VAKYN_API_KEY")
        code, out = self.run_cli("send", str(self.file), "--yes")
        self.assertEqual(code, 3)
        self.assertIn("vakyn.com/contact", out)
        self.assertEqual(self.fake.calls, [])

    def test_sent_with_key_and_yes(self):
        code, out = self.run_cli("send", str(self.file), "--yes")
        self.assertEqual(code, 0)
        method, path, auth, body = self.fake.calls[0]
        self.assertEqual((method, path, auth), ("POST", "/v1/training-requests", "Bearer vk_test"))
        self.assertEqual(body, SAMPLE)
        self.assertIn("console/training/tr_1", out)
        self.assertNotIn("vk_test", out)

    def test_api_answers(self):
        cases = [
            ((422, {"detail": {"errors": [{"path": "examples[0].made_up", "message": "must be true"}]}}, {}),
             1, "examples[0].made_up"),
            ((401, {"detail": "bad key"}, {}), 3, "vakyn.com/contact"),
            ((404, {}, {}), 3, "vakyn.com/contact"),
            ((429, {}, {"retry-after": "3600"}), 1, "3600"),
            ((413, {}, {}), 1, "128 KB"),
        ]
        for reply, code, text in cases:
            with self.subTest(status=reply[0]):
                self.fake.reply = reply
                got, out = self.run_cli("send", str(self.file), "--yes")
                self.assertEqual(got, code)
                self.assertIn(text, out)

    def test_status(self):
        self.fake.reply = (200, {"data": [{"id": "tr_1", "title": "Routing", "status": "quoted",
                                           "created_at": "2026-10-19T08:00:00Z", "updated_at": "2026-10-19T09:00:00Z",
                                           "url": "https://vakyn.com/console/training/tr_1", "quote": "EUR 4,000"}]}, {})
        code, out = self.run_cli("status")
        self.assertEqual(code, 0)
        self.assertIn("quoted", out)
        self.assertEqual(self.fake.calls[0][:2], ("GET", "/v1/training-requests"))


if __name__ == "__main__":
    unittest.main()
