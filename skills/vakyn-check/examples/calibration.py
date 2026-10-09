"""Calibration: does "0.9" mean right about 9 times in 10 on your own labeled records?

Usage:
    python3 calibration.py labeled.jsonl [--bins 0.5,0.7,0.8,0.9,0.95,1.0] [--question NAME]
        [--min-per-bin 30] [--chart reliability.png]

Same file as thresholds.py: one record VAKYN answered and a person labeled per line.
    choice / score: {"id": "t001", "vakyn_pick": "billing", "vakyn_confidence": 0.97, "label": "billing"}
    noul:           {"id": "n001", "noul": 0.93, "label": true}
Lines with a "question" field get one table per question.

choice / score: records are grouped by confidence; each group shows how many, the mean confidence,
the share VAKYN got right, and the gap between the two.
noul: records are grouped by the noul value itself (both sides, 0 to 1); each group shows the mean
noul and the share a person labeled true. Well calibrated means the two columns match.

Calibration error = the gap of each group, weighted by its share of records. The 95% range per group
shows how far its observed share could move with more records. Groups with fewer than --min-per-bin
records are marked; how many labels you need overall: references/thresholds.md.
Standard library only; --chart draws a picture when matplotlib is installed.
"""

import argparse
import json
import math

DEFAULT_EDGES = {"conf": [0.5, 0.7, 0.8, 0.9, 0.95, 1.0], "noul": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]}


def load(path):
    rows = []
    for line in open(path):
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("label") is None:
            continue  # not labeled yet
        q = r.get("question", "")
        if "noul" in r:  # predicted chance of yes vs. whether the person said yes
            rows.append({"q": q, "kind": "noul", "p": float(r["noul"]), "hit": bool(r["label"])})
            continue
        conf = r.get("vakyn_confidence", r.get("confidence"))
        if r.get("vakyn_pick") is None or conf is None:
            continue  # VAKYN failed on this record
        rows.append({"q": q, "kind": "conf", "p": float(conf), "hit": r["vakyn_pick"] == r["label"]})
    return rows


def wilson(k, n):
    """95% range for an observed share k/n."""
    if n == 0:
        return 0.0, 1.0
    z, p = 1.96, k / n
    mid = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, mid - half), min(1.0, mid + half)


def bin_rows(rows, edges):
    """Group i holds edges[i-1] < p <= edges[i]; the first group starts at 0 (inclusive)."""
    groups = []
    lo = 0.0
    for hi in edges:
        members = [r for r in rows if (lo < r["p"] <= hi) or (lo == 0.0 and r["p"] == 0.0)]
        groups.append((lo, hi, members))
        lo = hi
    return groups


def report(rows, edges, min_per_bin, kind):
    n = len(rows)
    observed = "share labeled true" if kind == "noul" else "share right"
    stated = "mean noul" if kind == "noul" else "mean confidence"
    print(f"{'group':<13} {'records':>7}  {stated:>15}  {observed:>18}  {'gap':>6}  95% range of observed")
    ece, signed, small = 0.0, 0.0, 0
    stats = []
    for lo, hi, m in bin_rows(rows, edges):
        if not m:
            continue
        k = sum(r["hit"] for r in m)
        mean_p = sum(r["p"] for r in m) / len(m)
        acc = k / len(m)
        gap = mean_p - acc
        ece += len(m) / n * abs(gap)
        signed += len(m) / n * gap
        a, b = wilson(k, len(m))
        flag = "  too few" if len(m) < min_per_bin else ""
        small += bool(flag)
        label = f"{'[' if lo == 0 else '('}{lo:.2f}, {hi:.2f}]"
        print(f"{label:<13} {len(m):>7}  {mean_p:>15.2f}  {acc:>18.2f}  {gap:>+6.2f}  {a:.2f} to {b:.2f}{flag}")
        stats.append((mean_p, acc, len(m)))
    print(f"\nCalibration error (weighted mean gap): {ece:.3f} over {n} records.")
    pts = round(ece * 100)
    word = "above" if signed > 0 else "below"
    if kind == "noul":
        print(f"Plain words: the noul value is off by about {pts} points, on average, from how often a person says "
              f"yes; on balance it sits {word} the observed share.")
    else:
        print(f"Plain words: stated confidence is off by about {pts} points, on average, from how often VAKYN "
              f"is right; on balance confidence sits {word} accuracy "
              f"({'too sure' if signed > 0 else 'too modest'} by {abs(signed) * 100:.0f} points).")
    if n < 50:
        print(f"Only {n} labeled records: too few to judge calibration. Use at least 50 to start; "
              "see references/thresholds.md for sample sizes.")
    if small:
        print(f"{small} group(s) have fewer than {min_per_bin} records: their share can move a lot with more "
              "labels (see the 95% range). Do not read calibration from those groups.")
    return stats


def chart(all_stats, path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed: no chart (the tables above hold the same numbers).")
        return
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], linestyle="--", color="grey", label="perfect")
    for name, stats in all_stats.items():
        xs, ys, ns = zip(*stats)
        ax.plot(xs, ys, marker="o", label=name or "all")
        for x, y, c in stats:
            ax.annotate(str(c), (x, y), textcoords="offset points", xytext=(4, -10), fontsize=7)
    ax.set_xlabel("stated (mean confidence or noul)")
    ax.set_ylabel("observed (share right or share true)")
    ax.legend()
    fig.savefig(path, dpi=120, bbox_inches="tight")
    print(f"Chart saved to {path}.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--bins", help="upper edges of the groups, comma-separated, ending at 1.0")
    ap.add_argument("--question", help="only this question, when the lines have a \"question\" field")
    ap.add_argument("--min-per-bin", type=int, default=30, help="mark groups smaller than this")
    ap.add_argument("--chart", help="save a reliability chart here (needs matplotlib)")
    a = ap.parse_args()

    rows = load(a.file)
    if a.question is not None:
        rows = [r for r in rows if r["q"] == a.question]
    if not rows:
        print("No labeled records.")
        return
    all_stats = {}
    for q in sorted({r["q"] for r in rows}):
        part = [r for r in rows if r["q"] == q]
        kind = part[0]["kind"]
        edges = [float(x) for x in a.bins.split(",")] if a.bins else DEFAULT_EDGES[kind]
        print(f"\n=== question: {q or '(none)'} ({'noul' if kind == 'noul' else 'choice/score confidence'}) ===")
        all_stats[q] = report(part, edges, a.min_per_bin, kind)
    if a.chart:
        chart(all_stats, a.chart)


if __name__ == "__main__":
    main()
