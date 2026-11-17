"""Save a VAKYN request as a short playground link and print it. Python standard library only.

Usage: python3 share_link.py vakyn-request.json
Needs VAKYN_API_KEY (vk_...). VAKYN_BASE_URL is optional (default https://api.vakyn.com).
"""

import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.environ.get("VAKYN_BASE_URL", "https://api.vakyn.com")


def share(request: dict, timeout: float = 30) -> str:
    """POST /v1/playground-links; returns the short link (https://vakyn.com/p/...)."""
    req = urllib.request.Request(
        f"{BASE_URL}/v1/playground-links",
        data=json.dumps(request).encode(),
        headers={"Authorization": f"Bearer {os.environ['VAKYN_API_KEY']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["url"]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    with open(sys.argv[1]) as f:
        request = json.load(f)
    if "VAKYN_API_KEY" not in os.environ:
        print("Set VAKYN_API_KEY (vakyn.com/console/keys) to make a link; until then, share the JSON file.", file=sys.stderr)
        return 1
    try:
        print(share(request))
    except urllib.error.HTTPError as e:
        print(f"VAKYN {e.code}: {e.read().decode(errors='replace')}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
