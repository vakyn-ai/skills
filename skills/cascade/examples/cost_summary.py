"""Summarize a cascade log: escalation, quality checks, tokens and cost per 1,000 requests.

Standard library only. Prices are yours, per million tokens, from your provider's price page:

  python3 cost_summary.py cascade-log.jsonl \
      --cheap-in <price> --cheap-out <price> --expensive-in <price> --expensive-out <price>

Without prices it reports tokens only. If your log has a `cost` field per model (some providers
return the cost of each call), that is used instead of tokens times prices.
"""

import argparse
import json
import statistics
from collections import Counter

p = argparse.ArgumentParser()
p.add_argument("log")
for name in ("cheap-in", "cheap-out", "expensive-in", "expensive-out"):
    p.add_argument(f"--{name}", type=float, help="price per million tokens")
args = p.parse_args()

lines = [json.loads(x) for x in open(args.log) if x.strip()]
prices = {"cheap": (args.cheap_in, args.cheap_out), "expensive": (args.expensive_in, args.expensive_out)}
priced = all(v is not None for pair in prices.values() for v in pair)


def pct(k, n):
    return f"{k}/{n} ({100 * k / n:.0f}%)" if n else "0/0"


def call_cost(line, model):
    """Cost of one model's call on one line, or None when it was not called or cannot be priced."""
    if (line.get("cost") or {}).get(model) is not None:
        return line["cost"][model]
    t = (line.get("tokens") or {}).get(model)
    if not t or not priced or t.get("in") is None:
        return None
    pin, pout = prices[model]
    return (t["in"] * pin + t["out"] * pout) / 1e6


def tokens(line, model):
    t = (line.get("tokens") or {}).get(model) or {}
    return (t.get("in") or 0) + (t.get("out") or 0)


for mode in ("side_by_side", "cascade"):
    rows = [x for x in lines if x.get("mode") == mode]
    if not rows:
        continue
    n = len(rows)
    failed = [x for x in rows if x.get("vakyn_pick") is None]
    print(f"\n== {mode}: {n} requests; VAKYN failed on {len(failed)} (treated as escalated)")
    routes = Counter(x.get("route") for x in rows)
    for r in ("accept_cheap", "escalate", "decline"):
        print(f"  {r:13} {pct(routes[r], n)}")
    print("  verdicts:", dict(Counter(x["vakyn_pick"] for x in rows if x.get("vakyn_pick"))))

    if mode == "side_by_side":
        acc = [x for x in rows if x.get("route") == "accept_cheap"]
        print(f"\n  Accepted cheap drafts vs the expensive answer (agreement, not accuracy): {len(acc)}")
        for k, c in Counter(x.get("chat_pick") for x in acc).most_common():
            print(f"    {str(k):17} {c}")
        labeled = [x for x in acc if x.get("label")]
        if labeled:
            worse = sum(x["label"] == "cheap_worse" for x in labeled)
            print(f"  Person spot-check of accepted drafts: worse on {pct(worse, len(labeled))}")
        else:
            print("  No person labels yet: add \"label\": \"cheap_ok\" or \"cheap_worse\" to a sample of accepted lines.")
        # Every line has both models' usage: compare the cascade with always-expensive directly.
        cascade_cost = [call_cost(x, "cheap") for x in rows] + [call_cost(x, "expensive") for x in rows if x.get("route") == "escalate"]
        always_cost = [call_cost(x, "expensive") for x in rows]
        cascade_tok = (sum(tokens(x, "cheap") for x in rows),
                       sum(tokens(x, "expensive") for x in rows if x.get("route") == "escalate"))
        always_tok = sum(tokens(x, "expensive") for x in rows)
        basis = "measured: the expensive model answered every request"
    else:
        print("  used:", dict(Counter(x.get("used") for x in rows)))
        esc = [x for x in rows if x.get("tokens", {}).get("expensive")]
        cascade_cost = [call_cost(x, "cheap") for x in rows] + [call_cost(x, "expensive") for x in esc]
        cascade_tok = (sum(tokens(x, "cheap") for x in rows), sum(tokens(x, "expensive") for x in rows))
        # Always-expensive is not observed here: estimate it from the escalated requests.
        mean_cost = statistics.mean(c for c in (call_cost(x, "expensive") for x in esc)) if esc and priced else None
        always_cost = [mean_cost] * n if mean_cost is not None else [None]
        always_tok = statistics.mean(tokens(x, "expensive") for x in esc) * n if esc else 0
        basis = f"estimated from the {len(esc)} escalated requests, which may be longer or harder than average"

    def path_ms(x, steps):
        return sum((x.get("ms") or {}).get(k, 0) for k in steps)
    for route, steps in (("accept_cheap", ("cheap", "check")), ("escalate", ("cheap", "check", "expensive", "check2"))):
        ms = [path_ms(x, steps) for x in rows if x.get("route") == route and x.get("ms")]
        if ms:
            print(f"  Median time, {route}: {statistics.median(ms):.0f} ms ({' + '.join(steps)}; side by side: what it would take)")

    print(f"\n  Tokens per 1,000 requests: cascade {1000 * cascade_tok[0] / n:,.0f} cheap + "
          f"{1000 * cascade_tok[1] / n:,.0f} expensive; always expensive {1000 * always_tok / n:,.0f} ({basis})")
    if None in cascade_cost or None in always_cost:
        print("  Cost per 1,000 requests: needs your prices "
              "(--cheap-in/--cheap-out/--expensive-in/--expensive-out, per million tokens)")
        continue
    c, a = 1000 * sum(cascade_cost) / n, 1000 * sum(always_cost) / n
    print(f"  Cost per 1,000 requests: cascade {c:.4f}, always expensive {a:.4f}, "
          f"saved {a - c:.4f} ({100 * (a - c) / a:.0f}%). VAKYN's own server cost is not included.")
    cheap_share = sum(call_cost(x, "cheap") for x in rows) / sum(always_cost)
    print(f"  Break-even: the cascade saves money while the escalation rate stays under {100 * (1 - cheap_share):.0f}%"
          f" (now {100 * routes['escalate'] / n:.0f}%)")
