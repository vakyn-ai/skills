"""Offline checks for the plugin: manifests, skills, links, voice, example requests.

Run with `make test` (python3 -m unittest discover tests).
"""

import json
import pathlib
import re
import unittest

from checklist import check

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = sorted(p for p in (ROOT / "skills").iterdir() if p.is_dir())
EXPECTED_SKILLS = {
    "vakyn", "vakyn-research", "vakyn-questions", "vakyn-convert", "vakyn-workflow", "vakyn-check",
    "vakyn-cascade", "vakyn-batch", "vakyn-judge", "vakyn-migrate", "vakyn-distill",
}
SKILL_MAX_LINES = 150

# Public text: everything a user reads.
PUBLIC_TEXT = [ROOT / "README.md", *ROOT.glob("skills/**/*.md")]

# Voice rules for public text. Case-sensitive patterns are marked.
BANNED = [
    (r"\bVakyn\b", "write VAKYN (brand) or vakyn (typed)"),
    (r"(?i)\bAI-powered\b", "say what it decides"),
    (r"(?i)\bintelligent\b", "say what it decides"),
    (r"(?i)\bsmart\b", "say what it decides"),
    (r"(?i)\bclassifiers?\b", "say decision model"),
    (r"(?i)\brevolutionary\b|\bgame-changing\b|\bcutting-edge\b", "hype"),
    (r"(?i)\bSystem One\b", "say System 1"),
    (r"(?i)\bthe Jev API\b", "say Jev-compatible API"),
    (r"(?i)\bcoming soon\b|\bin development\b", "no planning words"),
    (r"(?i)\bGGUF\b", "the release format is UQFF"),
    (r"(?i)\bfine-?tun", "no base model or fine-tune in public text"),
    
    (r"(?i)\bbeats GPT\b|\bbetter than GPT\b", "no vendor comparisons"),
    
    (r"/code/|/home/", "no local paths"),
]

LINK_RE = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def frontmatter(path):
    text = path.read_text()
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    fm = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


class Manifests(unittest.TestCase):
    def test_plugin_json(self):
        p = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        for field in ("name", "description", "version", "license"):
            self.assertIn(field, p)
        self.assertEqual(p["name"], "vakyn")
        self.assertRegex(p["version"], r"^\d+\.\d+\.\d+$")

    def test_marketplace_json(self):
        m = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
        self.assertEqual(m["name"], "vakyn-ai")
        self.assertEqual([p["name"] for p in m["plugins"]], ["vakyn"])


class Skills(unittest.TestCase):
    def test_only_known_skills(self):
        self.assertLessEqual({p.name for p in SKILLS}, EXPECTED_SKILLS)

    def test_frontmatter_and_length(self):
        for d in SKILLS:
            with self.subTest(skill=d.name):
                f = d / "SKILL.md"
                self.assertTrue(f.exists(), "missing SKILL.md")
                fm = frontmatter(f)
                self.assertIsNotNone(fm, "missing frontmatter")
                self.assertEqual(fm.get("name"), d.name)
                self.assertGreater(len(fm.get("description", "")), 40, "description too short to trigger")
                n = len(f.read_text().splitlines())
                self.assertLessEqual(n, SKILL_MAX_LINES, f"SKILL.md has {n} lines; move detail to references/")


class Links(unittest.TestCase):
    def test_relative_links_resolve(self):
        for f in PUBLIC_TEXT:
            for target in LINK_RE.findall(f.read_text()):
                if re.match(r"^[a-z]+:", target):
                    continue
                with self.subTest(file=str(f.relative_to(ROOT)), link=target):
                    self.assertTrue((f.parent / target).exists(), "broken link")


class Voice(unittest.TestCase):
    def test_banned_words(self):
        for f in PUBLIC_TEXT:
            text = f.read_text()
            for pattern, why in BANNED:
                for m in re.finditer(pattern, text):
                    line = text.count("\n", 0, m.start()) + 1
                    self.fail(f"{f.relative_to(ROOT)}:{line}: '{m.group(0)}' ({why})")


def example_requests():
    return sorted(ROOT.glob("skills/**/*.request.json"))


class ExampleRequests(unittest.TestCase):
    def test_examples_pass_checklist(self):
        for f in example_requests():
            with self.subTest(file=str(f.relative_to(ROOT))):
                errors, _ = check(json.loads(f.read_text()))
                self.assertEqual(errors, [])

    def test_weak_examples_are_caught(self):
        # *.weak.json files are deliberate bad requests (vakyn-questions before/after pairs):
        # the checklist must flag each one, or the pair teaches nothing the check can see.
        for f in sorted(ROOT.glob("skills/**/*.weak.json")):
            with self.subTest(file=str(f.relative_to(ROOT))):
                errors, warnings = check(json.loads(f.read_text()))
                self.assertTrue(errors or warnings, "weak example passes the checklist cleanly")


class Checklist(unittest.TestCase):
    def base(self, **q):
        return {"model": "jev-latest", "state": "x", "questions": {"q": q}}

    def test_good_request(self):
        req = self.base(type="choice", instructions="Which team handles state?",
                        criteria={"billing": "Charges", "other": "None of these fits"})
        self.assertEqual(check(req), ([], []))

    def test_errors(self):
        cases = [
            {"model": "jev-latest", "state": None, "questions": {"q": {"type": "noul", "instructions": "x?"}}},
            self.base(type="choice", instructions="Which?", criteria={"a": "A"}),
            self.base(type="choice", instructions="Which?", criteria={"a": "", "none": "n"}),
            self.base(type="score", instructions="How?", criteria=["1", "2", "3"]),
            self.base(type="score", instructions="How?", criteria=["only one"]),
            self.base(type="noul", instructions="Is it?", criteria={"yes": "y"}),
            self.base(type="rank", instructions="x"),
            self.base(type="choice", instructions="Which?", criteria={"a": None, "none": "n"}),
            self.base(type="choice", instructions="Which?", criteria={"a": {}, "none": "n"}),
            self.base(type="choice", instructions="Which?", criteria={"a": [], "none": "n"}),
            self.base(type="score", instructions="How?", criteria=[1, 2, 3]),
            self.base(type="score", instructions="How?", criteria=["none", {"level": ""}]),
            self.base(type="noul", instructions={}),
            self.base(type="noul", instructions=None),
            {"model": "jev-latest", "state": "x", "questions": {}, "stream": True},
        ]
        for req in cases:
            with self.subTest(req=req):
                self.assertNotEqual(check(req)[0], [])

    def test_structured_fields(self):
        # The server renders objects as `key: value` lines and lists as `- item` lines.
        req = self.base(
            type="choice",
            instructions={"question": "Which team should handle the customer's message?",
                          "note": "A refund for a broken product still goes to billing."},
            criteria={
                "billing": {"handles": "money already charged", "includes": ["refunds", "invoices"],
                            "not": "prices before buying (sales)"},
                "sales": ["prices", "plans", "trials"],
                "other": "Anything none of the teams above handle",
            })
        self.assertEqual(check(req), ([], []))
        req = self.base(type="score", instructions="How angry is the customer's message?",
                        criteria=["Calm: no complaint", {"level": "annoyed", "signs": ["sighs", "again"]},
                                  ["furious", "threatens to leave"]])
        self.assertEqual(check(req), ([], []))

    def test_warnings(self):
        cases = [
            self.base(type="choice", instructions="Which team?", criteria={"billing": "B", "access": "A"}),
            self.base(type="noul", instructions="Is it urgent and about billing?"),
            self.base(type="choice", instructions="Is option 2 right?", criteria={"a": "A", "none": "N"}),
        ]
        for req in cases:
            with self.subTest(req=req):
                errors, warnings = check(req)
                self.assertEqual(errors, [])
                self.assertNotEqual(warnings, [])

    def test_size_limit(self):
        req = self.base(type="noul", instructions="Is it?")
        req["state"] = "word " * 40_000
        self.assertNotEqual(check(req)[0], [])


if __name__ == "__main__":
    unittest.main()
