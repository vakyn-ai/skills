"""Summarize a side-by-side log: VAKYN and the chat model picked on the same requests.

Usage:
    python3 log_summary.py side-by-side.jsonl [--examples 10]

One JSON object per line (the format the converted app writes):
    {"ts": "...", "request_id": "req_...", "vakyn_pick": "refund_order", "vakyn_confidence": 0.91,
     "vakyn_probabilities": {...}, "chat_pick": "ask_user", "agree": false,
     "mode": "side_by_side", "used": "chat"}
Optional: "label" (what a person says is right). Agreement is not accuracy; only labels measure
accuracy. Standard library only.
"""

import argparse
import collections
import json

THRESHOLDS = [0.5, 0.7, 0.8, 0.9, 0.95]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--examples", type=int, default=10, help="disagreements to list for labeling")
    a = ap.parse_args()

    rows = [json.loads(line) for line in open(a.file) if line.strip()]
    rows = [r for r in rows if r.get("mode", "side_by_side") == "side_by_side" and r.get("chat_pick") is not None]
    n = len(rows)
    if not n:
        print("No side-by-side lines with both picks.")
        return
    for r in rows:
        r["agree"] = r["vakyn_pick"] == r["chat_pick"]  # recompute; never trust a stored flag blindly
    agree = sum(r["agree"] for r in rows)
    print(f"{n} requests, {rows[0]['ts']} to {rows[-1]['ts']}")
    print(f"Agreement: {agree}/{n} ({agree / n:.0%})")

    print("\nPer option (by the chat model's pick)")
    print("option              requests  agree  VAKYN picked instead")
    by_chat = collections.defaultdict(list)
    for r in rows:
        by_chat[r["chat_pick"]].append(r)
    for opt, rs in sorted(by_chat.items(), key=lambda kv: -len(kv[1])):
        ok = sum(r["agree"] for r in rs)
        other = collections.Counter(r["vakyn_pick"] for r in rs if not r["agree"])
        instead = ", ".join(f"{k} x{v}" for k, v in other.most_common()) or "-"
        print(f"  {opt:<18} {len(rs):>8}  {ok / len(rs):>5.0%}  {instead}")

    pairs = collections.Counter((r["chat_pick"], r["vakyn_pick"]) for r in rows if not r["agree"])
    print("\nConfusion pairs (chat model -> VAKYN)")
    for (c, v), k in pairs.most_common():
        print(f"  {c} -> {v}: {k}")

    print("\nIf VAKYN answers only at or above a threshold (the rest go to the chat model)")
    print("threshold  VAKYN answers  agreement on those  unsure (sent on)")
    for t in THRESHOLDS:
        hit = [r for r in rows if r["vakyn_confidence"] >= t]
        ok = sum(r["agree"] for r in hit)
        rate = f"{ok / len(hit):.0%}" if hit else "-"
        print(f"  >= {t:<5} {len(hit):>5} ({len(hit) / n:>4.0%})  {rate:>17}  {n - len(hit):>6} ({(n - len(hit)) / n:.0%})")

    labeled = [r for r in rows if r.get("label") is not None]
    if labeled:
        v = sum(r["vakyn_pick"] == r["label"] for r in labeled)
        c = sum(r["chat_pick"] == r["label"] for r in labeled)
        print(f"\nAgainst {len(labeled)} person labels: VAKYN right {v}, chat model right {c}")
    else:
        print("\nNo person labels yet: agreement only says they pick the same, not that either is right.")

    dis = sorted((r for r in rows if not r["agree"]), key=lambda r: -r["vakyn_confidence"])
    print(f"\nDisagreements to label first (most confident VAKYN first), {min(a.examples, len(dis))} of {len(dis)}")
    for r in dis[: a.examples]:
        print(f"  {r['request_id']}  VAKYN {r['vakyn_pick']} ({r['vakyn_confidence']:.2f})  chat {r['chat_pick']}")


if __name__ == "__main__":
    main()
