"""Layout checks for installing the skills outside Claude Code.

`npx skills add` (vercel-labs/skills) copies each `skills/<name>/` folder into the agent's skill
folder (`.agents/skills/<name>/` for Codex, Cursor and OpenCode). These checks guard what that
installer and the Agent Skills format (agentskills.io) need:

- every skill folder has a SKILL.md whose frontmatter parses as strict YAML, with `name` equal to
  the folder name and a `description` of at most 1024 characters;
- names are unique and follow the format (lowercase letters, digits, single hyphens);
- links that leave a skill folder land in another skill folder, never elsewhere in the repo,
  so they still resolve when the skills are installed side by side;
- nothing the installer drops (`metadata.json`, `__pycache__`) is linked to, and no symlinks.

Run with `make test`.
"""

import json
import os
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
SKILLS = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir() and p.name != "__pycache__")

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
DROPPED_FILES = {"metadata.json"}
DROPPED_DIRS = {"__pycache__", "__pypackages__", ".git"}

# Skills whose frontmatter strict YAML parsers reject today. The installer skips them with
# "YAML parse error". Fix: put the description in double quotes. Then remove the name here.
KNOWN_UNQUOTED = {"vakyn-convert", "vakyn-workflow"}


def raw_frontmatter(path):
    text = path.read_text()
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    return None if end == -1 else text[4:end]


def yaml_problems(block):
    """Strict-YAML problems in a flat `key: value` frontmatter block (stdlib only).

    Covers what trips js-yaml / PyYAML in practice: ': ' or ' #' inside a plain scalar, a plain
    scalar starting with an indicator, a double-quoted value that is not valid, a duplicate key.
    """
    problems, seen = [], set()
    for n, line in enumerate(block.splitlines(), 1):
        if not line.strip() or line.startswith((" ", "\t", "#")):
            continue  # nested values (metadata:) and comments are left to the full parser
        if ":" not in line:
            problems.append(f"line {n}: not a key: value pair")
            continue
        key, value = line.split(":", 1)
        if key in seen:
            problems.append(f"line {n}: duplicate key {key!r}")
        seen.add(key)
        value = value.strip()
        if not value:
            continue
        if value.startswith('"'):
            try:
                json.loads(value)
            except ValueError:
                problems.append(f"line {n}: {key} is not a valid double-quoted string")
        elif value.startswith("'"):
            if not (value.endswith("'") and len(value) > 1):
                problems.append(f"line {n}: {key} has an unclosed single quote")
        else:
            if value[0] in "-?:,[]{}#&*!|>%@`":
                problems.append(f"line {n}: {key} starts with YAML indicator {value[0]!r}; quote it")
            if ": " in value or value.endswith(":"):
                problems.append(f"line {n}: {key} contains ': '; quote it")
            if " #" in value:
                problems.append(f"line {n}: {key} contains ' #' (a YAML comment); quote it")
    return problems


def parse(block):
    """Frontmatter as a dict: PyYAML when installed, else the flat parser."""
    try:
        import yaml  # optional; CI runs stdlib only
    except ImportError:
        fm = {}
        for line in block.splitlines():
            if ":" in line and not line.startswith((" ", "\t")):
                k, v = line.split(":", 1)
                v = v.strip()
                fm[k.strip()] = json.loads(v) if v.startswith('"') else v.strip("'")
        return fm
    return yaml.safe_load(block)


class Frontmatter(unittest.TestCase):
    def test_strict_yaml(self):
        for d in SKILLS:
            if d.name in KNOWN_UNQUOTED:
                continue
            with self.subTest(skill=d.name):
                self.assertTrue((d / "SKILL.md").is_file(), "missing SKILL.md")
                block = raw_frontmatter(d / "SKILL.md")
                self.assertIsNotNone(block, "missing frontmatter")
                self.assertEqual(yaml_problems(block), [])

    def test_known_unquoted_still_listed(self):
        # When a listed skill is fixed, drop it from KNOWN_UNQUOTED so the strict check covers it.
        for name in sorted(KNOWN_UNQUOTED):
            d = SKILLS_DIR / name
            if not (d / "SKILL.md").exists():
                continue
            with self.subTest(skill=name):
                self.assertNotEqual(yaml_problems(raw_frontmatter(d / "SKILL.md")), [],
                                    f"{name} parses cleanly now: remove it from KNOWN_UNQUOTED")

    def test_name_and_description(self):
        names = []
        for d in SKILLS:
            with self.subTest(skill=d.name):
                f = d / "SKILL.md"
                self.assertTrue(f.is_file(), "missing SKILL.md")
                if d.name in KNOWN_UNQUOTED:
                    fm = {k.strip(): v.strip() for k, v in
                          (l.split(":", 1) for l in raw_frontmatter(f).splitlines() if ":" in l)}
                else:
                    fm = parse(raw_frontmatter(f))
                self.assertIsInstance(fm, dict)
                name, desc = fm.get("name"), fm.get("description")
                self.assertEqual(name, d.name, "name must equal the folder name")
                self.assertRegex(name, NAME_RE)
                self.assertLessEqual(len(name), 64)
                self.assertIsInstance(desc, str)
                self.assertTrue(0 < len(desc) <= 1024, f"description is {len(desc)} characters")
                names.append(name)
        self.assertEqual(len(names), len(set(names)), "skill names must be unique")


class InstalledLayout(unittest.TestCase):
    def test_links_stay_inside_installed_skills(self):
        skill_names = {d.name for d in SKILLS}
        for f in SKILLS_DIR.glob("*/**/*.md"):
            if DROPPED_DIRS & set(f.relative_to(SKILLS_DIR).parts):
                continue
            own = f.relative_to(SKILLS_DIR).parts[0]
            for target in LINK_RE.findall(f.read_text()):
                if re.match(r"^[a-z]+:", target) or target.startswith("/"):
                    continue
                resolved = pathlib.Path(os.path.normpath(f.parent / target))
                with self.subTest(file=str(f.relative_to(ROOT)), link=target):
                    self.assertTrue(resolved.is_relative_to(SKILLS_DIR),
                                    "link leaves skills/; the installer copies only skill folders")
                    parts = resolved.relative_to(SKILLS_DIR).parts
                    self.assertTrue(parts, "link points at skills/ itself")
                    if parts[0] != own:
                        self.assertIn(parts[0], skill_names, "link to a folder that is not a skill")
                        self.assertTrue((SKILLS_DIR / parts[0] / "SKILL.md").is_file(),
                                        "linked skill has no SKILL.md")
                    self.assertTrue(resolved.exists(), "broken link")
                    self.assertFalse(DROPPED_FILES & {resolved.name}, "the installer drops this file")
                    self.assertFalse(DROPPED_DIRS & set(parts), "the installer drops this folder")

    def test_no_symlinks_or_dropped_files(self):
        for p in SKILLS_DIR.rglob("*"):
            if DROPPED_DIRS & set(p.relative_to(SKILLS_DIR).parts):
                continue
            with self.subTest(path=str(p.relative_to(ROOT))):
                self.assertFalse(p.is_symlink(), "symlinks do not survive copy installs")
                self.assertNotIn(p.name, DROPPED_FILES, "the installer skips this file")


if __name__ == "__main__":
    unittest.main()
