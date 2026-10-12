"""Pick a confidence threshold from records a person labeled.

Usage:
    python3 thresholds.py labeled.jsonl [--target 0.02] [--holdout 0.3] [--seed 7]
    noul, when one kind of mistake costs more:
    python3 thresholds.py labeled.jsonl --cost-missed 25 --cost-false-flag 1 --cost-review 0.5

Each line of labeled.jsonl is one record VAKYN answered and a person labeled:
    choice / score: {"id": "t001", "vakyn_pick": "billing", "vakyn_confidence": 0.97, "label": "billing"}
    noul:           {"id": "n001", "noul": 0.93, "label": true}
A side-by-side log with a person's "label" added works too. Lines with a "question" field (a converted
prompt logs one line per question) get one threshold per question; --question picks one.

For each candidate threshold it prints coverage (share answered automatically) and the error rate
on the answered records, picks the lowest threshold that meets --target on the tuning part, then
checks that threshold on the held-out part it never saw. Lines where VAKYN failed (vakyn_pick null)
are skipped. Starting values and how many labels you need: references/thresholds.md. Standard
library only.
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
        q = r.get("question", "")
        if "noul" in r:  # yes/no: confidence is the distance from 0.5
            p = float(r["noul"])
            rows.append({"id": r.get("id"), "q": q, "pick": p >= 0.5, "conf": round(abs(2 * p - 1), 4),
                         "label": bool(r["label"]), "noul": p})
        else:
            conf = r.get("vakyn_confidence", r.get("confidence"))
            if r.get("vakyn_pick") is None or conf is None:
                continue  # VAKYN failed on this record: nothing to threshold
            rows.append({"id": r.get("id", r.get("request_id")), "q": q, "pick": r["vakyn_pick"], "conf": float(conf),
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


def cost_cutoffs(tune, check, a):
    """Separate cut-offs chosen by cost: flag (act on yes) at noul >= hi, clear (act on no) at noul <= lo,
    a person in between. Costs per case come from the person: clearing a real yes, flagging a no, a review."""
    def cost(rows, lo, hi):
        missed = sum(r["label"] for r in rows if r["noul"] <= lo)
        false_flag = sum(not r["label"] for r in rows if r["noul"] >= hi)
        review = sum(lo < r["noul"] < hi for r in rows)
        total = missed * a.cost_missed + false_flag * a.cost_false_flag + review * a.cost_review
        return total, missed, false_flag, review

    los = [0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5]
    his = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.97, 0.99, 1.0]
    grid = sorted(((cost(tune, lo, hi), lo, hi) for lo in los for hi in his if lo < hi),
                  key=lambda x: (x[0][0], x[0][3], x[1]))  # ties: fewer reviews, then the safer (lower) clear cut-off
    print(f"\nnoul, cut-offs by cost (clearing a real yes {a.cost_missed:g}, a false flag {a.cost_false_flag:g}, "
          f"a review {a.cost_review:g}); tuning part, {len(tune)} records")
    print("  clear at <=  flag at >=  cleared but yes  flagged but no  to a person  total cost")
    shown = [g for g in grid[:5]]
    same = [g for g in grid if (g[1], g[2]) == (0.2, 0.8)]
    for (total, missed, ff, review), lo, hi in shown + [s for s in same if s not in shown]:
        mark = "  <- starting values" if (lo, hi) == (0.2, 0.8) else ""
        print(f"  {lo:>10}  {hi:>9}  {missed:>15}  {ff:>14}  {review:>11}  {total:>10g}{mark}")
    (_, _, _, _), lo, hi = grid[0]
    print(f"Chosen: clear at noul <= {lo}, flag at noul >= {hi}, a person in between.")
    if check:
        total, missed, ff, review = cost(check, lo, hi)
        base = cost(check, 0.2, 0.8)[0]
        print(f"Held-out check ({len(check)} records): {missed} cleared but yes, {ff} flagged but no, {review} to a person; "
              f"cost {total:g} (starting values 0.2 / 0.8: {base:g}).")
    yes = sum(r["label"] for r in tune)
    if yes < 30:
        print(f"Only {yes} real yes cases in the tuning part: the low cut-off rests on very few of them. Label more.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--target", type=float, default=0.02, help="highest error rate you accept on answered records")
    ap.add_argument("--holdout", type=float, default=0.3, help="share of labels kept back to check the pick")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--question", help="only this question, when the lines have a \"question\" field")
    ap.add_argument("--cost-missed", type=float, help="noul: cost of clearing a case that was really yes")
    ap.add_argument("--cost-false-flag", type=float, default=1.0, help="noul: cost of flagging a case that was no")
    ap.add_argument("--cost-review", type=float, default=0.5, help="noul: cost of a person looking at one case")
    a = ap.parse_args()

    rows = load(a.file)
    if a.question is not None:
        rows = [r for r in rows if r["q"] == a.question]
    questions = sorted({r["q"] for r in rows})
    for q in questions:
        if len(questions) > 1 or q:
            print(f"\n=== question: {q or '(none)'} ===")
        report([r for r in rows if r["q"] == q], a)
    if not rows:
        print("No labeled records.")


def report(rows, a):
    if len(rows) < 50:
        print(f"Only {len(rows)} labeled records. Use at least 50 to start; a few hundred to prove a low error rate.")
    rng = random.Random(a.seed)
    rng.shuffle(rows)
    k = int(len(rows) * a.holdout)
    check, tune = rows[:k], rows[k:]

    overall = at(rows, 0.0)
    print(f"All {len(rows)} labeled records: {overall['errors']} wrong ({overall['error_rate']:.1%}) when every answer is used.")
    stats = table(tune, "Tuning part")
    chosen = choose(stats, a.target)
    if not chosen:
        print(f"\nNo threshold meets a {a.target:.1%} error rate. Fix the question first (questions), or accept a higher rate.")
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
        if a.cost_missed is not None:
            cost_cutoffs(tune, check, a)


if __name__ == "__main__":
    main()
