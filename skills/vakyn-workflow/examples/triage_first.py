"""Triage first, stop early: one noul per search hit in one request, open the dangerous hits first,
stop when nothing left could change the outcome. pip install typesafe-sdk

Needs TYPESAFE_BASE_URL and TYPESAFE_API_KEY. Opening a hit (fetching the full article, or a
research agent that reads it) is stubbed with FULL_TEXT below; replace open_hit() with yours.
"""

import concurrent.futures
import datetime

from typesafe_sdk import Choice, Noul, TypeSafeClient

SUPPLIER = ("Harlow Precision Castings Ltd, company number 08814522, Brightside Lane, Sheffield, UK. "
            "Aluminium die-casting. Directors: Meera Okafor, Tom Lindqvist. Founded 2013.")
BLOCKERS = ("Sanctions; fraud or bribery; insolvency or winding-up proceedings; "
            "a safety or environmental conviction or fine")
HITS = {  # what the search returned: a title and a snippet each, with the source's date
    "h01": ("2024-05-14", "Harlow Castings Inc. of Ohio fined $2.1M for falsifying safety test records."),
    "h02": ("2022-11-03", "Harlow Precision Castings wins the Sheffield Chamber of Commerce export award."),
    "h03": ("2026-03-09", "High Court list: winding-up petition presented against Harlow Precision Castings Ltd."),
    "h04": ("2026-08-21", "Harlow Precision Castings is hiring CNC operators at its Sheffield site."),
    "h05": ("2025-06-30", "Harlow Precision Cycles recalls 4,000 brake levers after a supplier defect."),
    "h06": ("2025-09-12", "Director Tom Lindqvist speaks at the UK casting industry conference."),
    "h07": ("2023-02-01", "Companies House notice: Harlow Precision Castings Ltd filed its annual accounts late."),
    "h08": ("2026-01-17", "Sanctions list update: Harlow Trading LLC (Dubai) added for export-control breaches."),
    "h09": ("2024-04-02", "Blog: ten die-casting suppliers in the UK worth a call, including Harlow Precision Castings."),
    "h10": ("2025-12-05", "Small fire at an industrial unit on Brightside Lane, Sheffield. No one was hurt."),
    "h11": ("2026-07-11", "Meera Okafor appointed director at Okafor Logistics."),
    "h12": ("2021-10-20", "Environment Agency fines Harlow Precision Castings Ltd £8,000 for a wastewater discharge breach."),
}
FULL_TEXT = {  # stub for open_hit(): what the full article says
    "h01": "Harlow Castings Inc., a foundry in Dayton, Ohio, USA, was fined $2.1M by the regulator for "
           "falsifying safety test records on pressure parts. The Ohio company has no subsidiaries abroad.",
    "h03": "In the High Court of Justice, Business and Property Courts in Leeds: a petition to wind up Harlow "
           "Precision Castings Ltd (company number 08814522), presented on 9 March 2026 by a creditor over "
           "unpaid invoices. Hearing set for 14 April 2026.",
    "h05": "Harlow Precision Cycles, a bicycle maker in Bristol, recalled brake levers. The parts came from a "
           "supplier in Taiwan. No other companies are named.",
    "h07": "Harlow Precision Castings Ltd (08814522) filed its 2022 accounts eleven days late. No penalty "
           "beyond the standard late filing fee was recorded.",
    "h08": "Harlow Trading LLC, registered in Dubai, was added to the sanctions list for re-exporting "
           "controlled machine tools. Its owner is listed as a Dubai resident.",
    "h10": "Fire crews put out a small fire in a waste skip behind units 4 to 6 on Brightside Lane, Sheffield, "
           "on Friday night. The cause is not known. No company was named and no one was hurt.",
    "h12": "The Environment Agency fined Harlow Precision Castings Ltd of Sheffield £8,000 after a wastewater "
           "discharge breach at its Brightside Lane site in October 2021.",
}
TODAY = datetime.date(2026, 10, 12)
LOOKBACK_YEARS = 3          # code rule: older events do not block
COULD_STOP_AT = 0.2         # starting values; set yours with vakyn-check. Unsure counts as dangerous.
SAME_AT, BLOCKER_AT = 0.8, 0.8
WAVE = 3                    # hits opened in parallel per wave

client = TypeSafeClient(timeout=60.0)


def triage_questions(hits):
    return {
        f"could_stop_{hid}": Noul(
            instructions=f"Suppose search hit {hid} in state.hits is about the supplier in state.supplier, even "
                         "if the name, place or company type differs. Does the hit report one of the blockers "
                         "in state.blockers?",
            criteria={"true": "The hit reports, or may report, a blocker in state.blockers, whoever it names",
                      "false": "The hit reports nothing on that list (awards, hiring, people, ordinary "
                               "filings, events with no wrongdoing)"})
        for hid in hits
    }


def triage(hits):
    """One request: one noul per hit, all over the same state. Returns {hit: probability it could stop}."""
    state = {"supplier": SUPPLIER, "blockers": BLOCKERS,
             "hits": {hid: f"{date}: {text}" for hid, (date, text) in hits.items()}}
    r = client.system_one(state=state, questions=triage_questions(hits))
    return {hid: r.nouls[f"could_stop_{hid}"].noul for hid in hits}, r.request_id


def open_hit(hid):
    return FULL_TEXT.get(hid, HITS[hid][1])  # your fetch or research step goes here


BLOCKER_KINDS = {
    "sanctions": "The company is on a sanctions list",
    "fraud_or_bribery": "The company is accused of or convicted for fraud, bribery or falsified records",
    "insolvency": "Insolvency, administration or winding-up proceedings against the company",
    "safety_or_environment": "A safety or environmental conviction or fine against the company",
    "none": "None of these is reported against the company",
}


def confirm(hid):
    """Open one hit and ask: is it really this supplier, and which blocker does it report?"""
    doc = open_hit(hid)
    r = client.system_one(
        state={"supplier": SUPPLIER, "document": doc},
        questions={
            "same_company": Noul(instructions="Is the company state.document is about the same company as "
                                              "state.supplier (same name, country, and number or address)?"),
            "blocker": Choice(instructions="Suppose state.document is about the supplier. Which of these does it "
                                           "report against that company?", criteria=BLOCKER_KINDS),
        })
    same, kind = r.nouls["same_company"].noul, r.choices["blocker"]
    date = datetime.date.fromisoformat(HITS[hid][0])
    recent = (TODAY - date).days <= 365 * LOOKBACK_YEARS
    if same < 1 - SAME_AT:
        verdict = "not this supplier"
    elif same < SAME_AT or kind.choice not in BLOCKER_KINDS or kind.confidence < BLOCKER_AT:
        verdict = "unsure: to a person"
    elif kind.choice == "none":
        verdict = "this supplier, no blocker"
    elif not recent:
        verdict = f"this supplier, {kind.choice}, older than {LOOKBACK_YEARS} years: does not block"
    else:
        verdict = f"BLOCKER: {kind.choice}"
    return {"hit": hid, "same_company": round(same, 2), "blocker": kind.choice,
            "blocker_confidence": round(kind.confidence, 2), "verdict": verdict, "request_id": r.request_id}


def review(hits):
    could, triage_id = triage(hits)
    order = sorted((h for h in hits if could[h] >= COULD_STOP_AT), key=lambda h: -could[h])
    log = {h: {"could_stop": round(could[h], 2), "opened": False,
               "why_not_opened": f"could_stop {could[h]:.2f} < {COULD_STOP_AT}: cannot change the outcome"}
           for h in hits if h not in order}
    outcome = "clear"
    with concurrent.futures.ThreadPoolExecutor(max_workers=WAVE) as pool:
        for i in range(0, len(order), WAVE):
            wave = order[i:i + WAVE]
            for res in pool.map(confirm, wave):
                log[res["hit"]] = {"could_stop": round(could[res["hit"]], 2), "opened": True, **res}
            if any(log[h]["verdict"].startswith("BLOCKER") for h in wave):
                outcome = "stop: blocker found"
                for h in order[i + WAVE:]:
                    log[h] = {"could_stop": round(could[h], 2), "opened": False,
                              "why_not_opened": "outcome already decided by a confirmed blocker"}
                break
    if outcome == "clear" and any(v.get("verdict", "").startswith("unsure") for v in log.values()):
        outcome = "to a person: a hit could not be settled"
    return outcome, triage_id, log


if __name__ == "__main__":
    # The search as returned, then the same search without the court listing (h03).
    for hits in (HITS, {h: v for h, v in HITS.items() if h != "h03"}):
        outcome, triage_id, log = review(hits)
        print(f"triage request {triage_id}")
        for hid in sorted(log, key=lambda h: -log[h]["could_stop"]):
            e = log[hid]
            detail = e["verdict"] if e["opened"] else "not opened: " + e["why_not_opened"]
            print(f"  {hid}  could_stop {e['could_stop']:.2f}  {detail}")
        opened = sum(e["opened"] for e in log.values())
        print(f"outcome: {outcome}  (opened {opened} of {len(hits)} hits)\n")
