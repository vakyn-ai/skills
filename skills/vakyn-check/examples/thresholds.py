"""Pick a confidence threshold from records a person labeled.

Usage:
    python3 thresholds.py labeled.jsonl [--target 0.02] [--holdout 0.3] [--seed 7]

Each line of labeled.jsonl is one record VAKYN answered and a person labeled:
    choice / score: {"id": "t001", "vakyn_pick": "billing", "vakyn_confidence": 0.97, "label": "billing"}
    noul:           {"id": "n001", "noul": 0.93, "label": true}

For each candidate threshold it prints coverage (share answered automatically) and the error rate
on the answered records, picks the lowest threshold that meets --target on the tuning part, then
checks that threshold on the held-out part it never saw. A side-by-side log with a person's
"label" added to some lines works as it is. Standard library only.
"""

import argparse
import json
import random

CANDIDATES = [0.0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.97, 0.99]


def load(path):
    rows = []
    for line in open(path):
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("label") is None:
            continue  # not labeled yet
        if "noul" in r:  # yes/no: confidence is the distance from 0.5
            p = float(r["noul"])
            rows.append({"id": r.get("id"), "pick": p >= 0.5, "conf": round(abs(2 * p - 1), 4),
                         "label": bool(r["label"]), "noul": p})
        else:
            rows.append({"id": r.get("id"), "pick": r["vakyn_pick"], "conf": float(r.get("vakyn_confidence", r.get("confidence"))),
                         "label": r["label"], "text": r.get("text", "")})
    return rows


def upper95(errors, n):
    """One-sided 95% upper bound on the true error rate (exact binomial)."""
    if n == 0:
        return 1.0
    if errors >= n:
        return 1.0

    def cdf(p):
        total, term = 0.0, (1 - p) ** n
        for k in range(errors + 1):
            total += term
            term *= (n - k) / (k + 1) * p / (1 - p) if p < 1 else 0
        return total

    lo, hi = errors / n, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if cdf(mid) > 0.05 else (lo, mid)
    return hi


def at(rows, t):
    answered = [r for r in rows if r["conf"] >= t]
    errors = sum(r["pick"] != r["label"] for r in answered)
    n = len(answered)
    return {"t": t, "n": n, "coverage": n / len(rows) if rows else 0.0, "errors": errors,
            "error_rate": errors / n if n else 0.0, "upper": upper95(errors, n)}


def table(rows, title):
    print(f"\n{title} ({len(rows)} records)")
    print("threshold  answered  coverage  errors  error rate  error rate could be up to (95%)")
    stats = [at(rows, t) for t in CANDIDATES]
    for s in stats:
        print(f"  >= {s['t']:<5} {s['n']:>8}  {s['coverage']:>7.0%}  {s['errors']:>6}  {s['error_rate']:>9.1%}  {s['upper']:>10.1%}")
    return stats


def choose(stats, target):
    """Lowest threshold where it and every higher candidate meet the target."""
    chosen = None
    for s in reversed(stats):
        if s["n"] and s["error_rate"] <= target:
            chosen = s
        else:
            break
    return chosen


def noul_sides(rows, target):
    """Separate cut-offs: act on yes when noul >= hi, on no when noul <= lo."""
    print("\nnoul, separate cut-offs (each side meets the target on its own)")
    for side, want in (("yes", True), ("no", False)):
        best = None
        for c in sorted({0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99}, reverse=True):
            hit = [r for r in rows if (r["noul"] >= c if want else r["noul"] <= round(1 - c, 4))]
            err = sum(r["label"] != want for r in hit)
            if hit and err / len(hit) <= target:
                best = (c, len(hit), err)
            else:
                break
        if best:
            cut = best[0] if want else round(1 - best[0], 2)
            op = ">=" if want else "<="
            print(f"  {side}: act when noul {op} {cut}: {best[1]} records, {best[2]} wrong")
        else:
            print(f"  {side}: no cut-off meets the target; send every {side} to review")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--target", type=float, default=0.02, help="highest error rate you accept on answered records")
    ap.add_argument("--holdout", type=float, default=0.3, help="share of labels kept back to check the pick")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    rows = load(a.file)
    if len(rows) < 50:
        print(f"Only {len(rows)} labeled records. Use at least 50; a few hundred give a firmer number.")
    rng = random.Random(a.seed)
    rng.shuffle(rows)
    k = int(len(rows) * a.holdout)
    check, tune = rows[:k], rows[k:]

    overall = at(rows, 0.0)
    print(f"All {len(rows)} labeled records: {overall['errors']} wrong ({overall['error_rate']:.1%}) when every answer is used.")
    stats = table(tune, "Tuning part")
    chosen = choose(stats, a.target)
    if not chosen:
        print(f"\nNo threshold meets a {a.target:.1%} error rate. Fix the question first (vakyn-questions), or accept a higher rate.")
        return
    print(f"\nChosen: confidence >= {chosen['t']}: answers {chosen['coverage']:.0%} automatically, "
          f"{chosen['errors']} of {chosen['n']} wrong on the tuning part.")
    if chosen["upper"] > a.target:
        print(f"Too few records to prove {a.target:.1%}: with {chosen['n']} answered the true rate could be up to "
              f"{chosen['upper']:.1%}. Label more records before trusting it.")
    if check:
        c = at(check, chosen["t"])
        print(f"Held-out check ({len(check)} records): answers {c['coverage']:.0%}, {c['errors']} of {c['n']} wrong "
              f"({c['error_rate']:.1%}). {'Meets' if c['error_rate'] <= a.target else 'Misses'} the target.")
    wrong = sorted((r for r in rows if r["conf"] >= chosen["t"] and r["pick"] != r["label"]), key=lambda r: -r["conf"])
    if wrong:
        print("\nConfident mistakes at the chosen threshold (check the question and the label):")
        for r in wrong:
            print(f"  {r['id']}: VAKYN {r['pick']} ({r['conf']:.2f}), person {r['label']}  {r.get('text', '')[:60]}")
    if rows and "noul" in rows[0]:
        noul_sides(rows, a.target)


if __name__ == "__main__":
    main()
