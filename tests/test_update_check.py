"""The skills' update check: a notice for an older copy, silence otherwise."""

import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("update_check", ROOT / "skills/get-started/examples/update_check.py")
update_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update_check)


def models(latest):
    return {"models": [], "skills": {"latest": latest, "update": "claude plugin update vakyn@vakyn-ai",
                                     "update_other_agents": "npx skills update -y"}}


class UpdateCheck(unittest.TestCase):
    def test_version_matches_the_plugin(self):
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        self.assertEqual(update_check.VERSION, plugin["version"])

    def test_older_copy_gets_one_line_with_both_commands(self):
        notice = update_check.update_notice(models("0.10.0"), "0.9.0")
        self.assertIn("0.10.0", notice)
        self.assertIn("claude plugin update vakyn@vakyn-ai", notice)
        self.assertIn("npx skills update -y", notice)
        self.assertNotIn("\n", notice)

    def test_same_or_newer_copy_stays_quiet(self):
        self.assertIsNone(update_check.update_notice(models("0.9.0"), "0.9.0"))
        self.assertIsNone(update_check.update_notice(models("0.8.1"), "0.9.0"))

    def test_missing_or_odd_field_stays_quiet(self):
        self.assertIsNone(update_check.update_notice({"models": []}, "0.9.0"))
        self.assertIsNone(update_check.update_notice(models("next"), "0.9.0"))
        self.assertIsNone(update_check.update_notice(None, "0.9.0"))


if __name__ == "__main__":
    unittest.main()
