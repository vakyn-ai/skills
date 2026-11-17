"""Tell the person once when a newer release of the VAKYN skills is out.

GET /v1/models (free, no key) returns `skills.latest` and the update commands. Prints one line when this copy
is older, and nothing otherwise; never fails the caller (no network, a self-hosted server without the field).
Base URL from VAKYN_BASE_URL or TYPESAFE_BASE_URL, default https://api.vakyn.com.
"""

import json
import os
import urllib.request

# This copy's version; `make release` keeps it equal to .claude-plugin/plugin.json.
VERSION = "0.9.0"


def parse(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return None


def update_notice(models, version=VERSION):
    """The line to show for a /v1/models response, or None when this copy is current."""
    skills = (models or {}).get("skills") or {}
    latest, mine = parse(skills.get("latest")), parse(version)
    if not latest or not mine or latest <= mine:
        return None
    how = skills.get("update", "claude plugin update vakyn@vakyn-ai")
    others = skills.get("update_other_agents", "npx skills update -y")
    return (f"A newer release of the VAKYN skills is out ({skills['latest']}; this copy is {version}). "
            f"Update with `{how}` in Claude Code, or `{others}` for other agents.")


def main():
    base = os.environ.get("VAKYN_BASE_URL") or os.environ.get("TYPESAFE_BASE_URL") or "https://api.vakyn.com"
    try:
        with urllib.request.urlopen(f"{base.rstrip('/')}/v1/models", timeout=5) as r:
            notice = update_notice(json.load(r))
    except Exception:
        return
    if notice:
        print(notice)


if __name__ == "__main__":
    main()
