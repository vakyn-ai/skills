"""Supplier onboarding as a program: plain code, VAKYN questions and one small agent step.

Distilled from the agent runs in traces.sample.jsonl and the procedure in sop.sample.md.
Steps and kinds (step map in step-map.md):
  intake    VAKYN route + classify-from-schema, one request   -> stop early if not an application
  documents code: required slots and dates
  bank      code: bank country vs registered country           -> stop early: compliance outranks all
  sift      VAKYN, the same yes/no for every screening hit, one request; drop clear noes
  look-up   small agent step per kept hit, most likely first   -> stop early on an exact registration number
  pick      VAKYN, one kept hit or none                        -> a match or "cannot tell" goes to compliance
  outcome   code: the procedure's order of outcomes
Unsure VAKYN answers go back to the agent (the old flow, as a whole case). Every request writes a
decision record to decisions.jsonl.

pip install typesafe-sdk. Needs TYPESAFE_BASE_URL and TYPESAFE_API_KEY.
  python program.py traces.sample.jsonl                     # all cases, then the report
  python program.py traces.sample.jsonl --case sup-0108 --save-requests out/
  python program.py traces.sample.jsonl --replay decisions.jsonl --set sift_drop_at=0.1   # no server calls
"""

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import time
from dataclasses import dataclass, field

from typesafe_sdk import Choice, Noul, TypeSafeClient

PROGRAM_VERSION = "supplier-onboarding 1"
# Thresholds are versioned settings. Starting values from check/references/thresholds.md;
# tuned later on labeled cases with the check skill. Change a number -> change the version.
SETTINGS = {
    "version": "thresholds-2026-10-12a",
    "route_min_confidence": 0.8,
    "classify_yes": 0.8,       # noul at or above: yes
    "classify_no": 0.2,        # noul at or below: no; between: unsure -> agent
    "sift_drop_at": 0.2,       # asymmetric: a hit is dropped only on a clear no; a missed match costs far more than a look-up
    "pick_min_confidence": 0.8,
}
DECISIONS = pathlib.Path("decisions.jsonl")
client = TypeSafeClient(timeout=120.0)


# ---------- typed records passed between steps ----------
@dataclass
class Case:
    case_id: str
    received: str
    email: str
    company: dict
    documents: list
    bank_country: str
    payment_terms: str
    hits: list


@dataclass
class Result:
    case_id: str
    outcome: str = ""                 # one of the procedure's outcomes
    handled_by: str = "program"       # "program", or "agent" when an unsure answer sent it back
    reasons: list = field(default_factory=list)
    missing_documents: list = field(default_factory=list)
    matched_hit: str | None = None
    vakyn_requests: int = 0
    lookups: int = 0
    vakyn_ms: int = 0


# ---------- VAKYN questions ----------
# The agent's final output schema, compiled to questions: enum -> choice, bool -> noul.
INTAKE_QUESTIONS = {
    "route": {"type": "choice", "instructions": "What kind of email is state.email? state.portal_documents lists what the sender uploaded to our supplier portal.", "criteria": {
        "new_application": "A company asks to become our supplier: it offers to supply us and applies, or says its documents are in the portal",
        "existing_supplier_change": "A supplier already on file asks to change its details, bank account or contacts",
        "invoice_or_payment": "An invoice, a payment reminder or a question about a payment",
        "sales_pitch": "Marketing that does not apply to become a supplier: a demo invitation, a discount, a newsletter",
        "other": "None of these, or it cannot be told from the email"}},
    "category": {"type": "choice", "instructions": "What will the company in state.email supply?", "criteria": {
        "goods": "Physical products delivered to us: materials, parts, tools, packaging",
        "services": "Work done on our sites or for our staff: cleaning, catering, maintenance, consulting",
        "software": "Licenses, hosted tools or data services",
        "logistics": "Transport, storage or customs handling of goods",
        "unclear": "The email does not say what it will supply"}},
    "handles_personal_data": {"type": "noul",
        "instructions": "Will the company in state.email handle personal data about our people (staff, customers)?",
        "criteria": {"true": "It will receive or store records about people: employee or customer records, payroll, HR data, contact lists",
                     "false": "It works with goods, premises, company data or anonymous figures; serving or meeting our staff is not handling their data"}},
    "nonstandard_terms": {"type": "noul",
        "instructions": "Do the payment terms in state.payment_terms differ from our standard terms (payment 30 days, 45 days after invoice)?",
        "criteria": {"true": "Shorter than 30 days, payment before delivery, a deposit or part paid in advance, or an early-payment discount",
                     "false": "Payment 30 or 45 days after invoice, monthly or yearly invoicing included"}},
}

SIFT_RUBRIC = {
    "true": "A similar name AND at least one of: the same country, the same address or street, or a person named in both. "
            "Names are similar when they share their main distinctive word (Halden Tools Ltd and Halden Trading GmbH share Halden), "
            "whatever the legal form (Ltd, GmbH, SRL, BV) and the other words.",
    "false": "The names share no distinctive word, or they do but nothing else matches: "
             "a different country, a different address and no person in common.",
}


def sift_questions(hits: list) -> dict:
    """Sift: the same yes/no for every item of a list, one request."""
    return {f"could_be_{h['id']}": {"type": "noul", "criteria": SIFT_RUBRIC, "instructions":
            f"Could the watch-list entry state.hits.{h['id']} be the same company as state.applicant?"} for h in hits}


def pick_question(kept: list) -> dict:
    """Pick: one item or none, with the registry records the look-up step found."""
    opts = {h["id"]: f"The watch-list entry {h['id']} ({h['name']}, {h['country']}) is the applicant" for h in kept}
    opts["none_of_these"] = "None of the entries is the applicant: registration number, address and directors differ"
    opts["cannot_tell"] = "The records conflict or are missing, so a person must decide"
    return {"match": {"type": "choice", "criteria": opts, "instructions":
            "Compare state.applicant with each watch-list entry in state.hits and its registry record in state.registry. "
            "Which entry, if any, is the applicant? The same registration number or the same directors and address mean it is."}}


# ---------- the small agent step (stub) ----------
REGISTRY = {  # canned results, standing in for the agent's registry search
    "Orvane Trading S.R.L.": {"reg_no": "J12/4471/2017", "address": "Str. Fabricii 22, Cluj-Napoca", "directors": ["Ana Rus", "Mihai Dobre"]},
    "Orvane Holdings Ltd": {"reg_no": "HE 388120", "address": "Arch. Makariou 41, Limassol", "directors": ["Mihai Dobre", "Eleni Charalambous"]},
    "Marlow Finch Trading Ltd": {"reg_no": "07741020", "address": "Unit 9, Docklands Way, London E16", "directors": ["Victor Hale"]},
}


def registry_lookup(hit: dict) -> dict:
    """Stub. In production: a small agent (any harness) with one tool, the registry search, and an
    output schema {reg_no, address, directors, source_url}; each field is checked against the page it
    cites before the program uses it. Never a paid call from this example."""
    return REGISTRY.get(hit["name"], {"reg_no": None, "address": None, "directors": [], "note": "no record found"})


# ---------- plumbing: requests and the decision record ----------
def qhash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:12]


STORED: dict = {}  # filled by --replay: answers already given, keyed by case, step, question and input


def ask(res: Result, step: str, state: dict, questions: dict, save: pathlib.Path | None) -> dict:
    """One VAKYN request; returns the answers as plain dicts and writes the decision record."""
    if save:
        save.mkdir(parents=True, exist_ok=True)
        (save / f"{step}.request.json").write_text(json.dumps(
            {"model": "jev-latest", "state": state, "questions": questions}, indent=2) + "\n")
    key = (res.case_id, step, qhash(questions), qhash(state))
    if key in STORED:  # replay: same question, same input -> stored answer, no server call
        return STORED[key]
    if STORED:         # replaying, and this question or its input is new: it needs a live answer
        raise LookupError(f"{step} needs a new answer")
    sdk = {k: (Choice if q["type"] == "choice" else Noul)(instructions=q["instructions"], criteria=q["criteria"])
           for k, q in questions.items()}
    t = time.perf_counter()
    r = client.system_one(state=state, questions=sdk)
    ms = int((time.perf_counter() - t) * 1000)
    res.vakyn_requests += 1
    res.vakyn_ms += ms
    answers = {k: a.model_dump(exclude_none=True) for k, a in r.answers.items()}
    record({"case_id": res.case_id, "step": step, "model": r.model, "request_id": r.request_id,
            "question_hash": key[2], "input_hash": key[3], "state": state, "answers": answers, "ms": ms})
    return answers


def record(row: dict) -> None:
    """Decision record: who answered, on what, under which versions. It holds case data: store it
    where the case files live. Replaying it re-decides every case without the server."""
    row = {"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "program": PROGRAM_VERSION,
           "settings": SETTINGS["version"], **row}
    with DECISIONS.open("a") as f:
        f.write(json.dumps(row) + "\n")


def back_to_agent(res: Result, why: str) -> Result:
    res.handled_by, res.outcome = "agent", "agent_fallback"
    res.reasons.append(why)
    return res


# ---------- the program ----------
def run_case(c: Case, save: pathlib.Path | None = None) -> Result:
    res = Result(c.case_id)
    S = SETTINGS
    # 1. intake: route + classify, one request
    state = {"email": c.email, "payment_terms": c.payment_terms or "not stated",
             "portal_documents": [d["slot"] for d in c.documents] or "none uploaded"}
    a = ask(res, "intake", state, INTAKE_QUESTIONS, save)
    route, cat = a["route"], a["category"]
    if route["confidence"] < S["route_min_confidence"]:
        return back_to_agent(res, f"route unsure ({route['choice']} {route['confidence']:.2f})")
    if route["choice"] != "new_application":
        res.outcome = "not_an_application"
        res.reasons.append(f"route {route['choice']}")
        return res                                                        # early stop
    if cat["choice"] == "unclear" or cat["confidence"] < S["route_min_confidence"]:
        return back_to_agent(res, f"category unsure ({cat['choice']} {cat['confidence']:.2f})")
    flags = {}
    for k in ("handles_personal_data", "nonstandard_terms"):
        p = a[k]["noul"]
        if S["classify_no"] < p < S["classify_yes"]:
            return back_to_agent(res, f"{k} unsure ({p:.2f})")
        flags[k] = p >= S["classify_yes"]

    # 2. documents: code
    today = dt.date.fromisoformat(c.received)
    have = {d["slot"]: d for d in c.documents}
    need = ["registration_certificate", "tax_certificate", "bank_letter"]
    need += ["insurance_certificate"] if cat["choice"] in ("services", "logistics") else []
    need += ["data_processing_agreement"] if flags["handles_personal_data"] else []
    for slot in need:
        d = have.get(slot)
        if (d is None
                or (slot == "tax_certificate" and (today - dt.date.fromisoformat(d["issued"])).days > 365)
                or (slot == "insurance_certificate" and dt.date.fromisoformat(d["expires"]) < today)):
            res.missing_documents.append(slot)

    # 3. bank: code. Compliance outranks every later outcome, so nothing left can change it.
    if c.bank_country != c.company["country"]:
        res.outcome = "escalate_compliance"
        res.reasons.append(f"bank country {c.bank_country} is not {c.company['country']}")
        return res                                                        # early stop

    # 4. screening: sift, look up the kept hits most likely first, then pick
    if c.hits:
        state = {"applicant": c.company, "hits": {h["id"]: h for h in c.hits}}
        a = ask(res, "sift", state, sift_questions(c.hits), save)
        scored = sorted(((a[f"could_be_{h['id']}"]["noul"], h) for h in c.hits), key=lambda x: -x[0])
        kept = [h for p, h in scored if p > S["sift_drop_at"]]
        res.reasons.append(f"sift kept {len(kept)} of {len(c.hits)}")
        registry = {}
        for h in kept:                                                    # most likely first
            registry[h["id"]] = registry_lookup(h)
            res.lookups += 1
            if registry[h["id"]]["reg_no"] == c.company["reg_no"]:       # exact: code decides, stop
                res.outcome, res.matched_hit = "escalate_compliance", h["id"]
                res.reasons.append(f"{h['id']} has the applicant's registration number")
                return res
        if kept:
            state = {"applicant": c.company, "hits": {h["id"]: h for h in kept}, "registry": registry}
            m = ask(res, "pick", state, pick_question(kept), save)["match"]
            if m["choice"] == "cannot_tell":
                res.outcome = "escalate_compliance"
                res.reasons.append("pick: cannot tell")
                return res
            if m["confidence"] < S["pick_min_confidence"]:
                return back_to_agent(res, f"pick unsure ({m['choice']} {m['confidence']:.2f})")
            if m["choice"] != "none_of_these":
                res.outcome, res.matched_hit = "escalate_compliance", m["choice"]
                res.reasons.append(f"pick {m['choice']} {m['confidence']:.2f}")
                return res

    # 5. outcome: code, in the procedure's order
    if res.missing_documents:
        res.outcome = "request_documents"
    elif flags["nonstandard_terms"]:
        res.outcome = "escalate_finance"
    else:
        res.outcome = "approve"
    return res


def report(rows: list) -> None:
    """Measured on this run; agent figures are as logged in the traces."""
    n = len(rows)
    handled = [(t, r) for t, r in rows if r.handled_by == "program"]
    agree = [(t, r) for t, r in handled if r.outcome == t["label"]]
    print(f"\ncases {n} | handled by the program {len(handled)} ({len(handled) / n:.0%}) | "
          f"back to the agent {n - len(handled)} ({(n - len(handled)) / n:.0%})")
    print(f"agreement with labels on handled cases: {len(agree)}/{len(handled)}")
    print(f"agent (traces):   tool calls per case {sum(len(t['steps']) for t, _ in rows) / n:.1f}, "
          f"cost per case ${sum(t['cost_usd'] for t, _ in rows) / n:.2f}, "
          f"agreement with labels {sum(t['final_output']['outcome'] == t['label'] for t, _ in rows)}/{n}")
    print(f"program (this run): VAKYN requests per case {sum(r.vakyn_requests for _, r in rows) / n:.1f}, "
          f"look-ups per case {sum(r.lookups for _, r in rows) / n:.1f}, "
          f"VAKYN time per case {sum(r.vakyn_ms for _, r in rows) / n / 1000:.1f} s")
    for t, r in rows:
        if r.handled_by == "program" and r.outcome != t["label"]:
            print(f"  review {r.case_id}: program {r.outcome}, label {t['label']} ({'; '.join(r.reasons)})")
        if r.handled_by == "agent":
            print(f"  agent  {r.case_id}: {'; '.join(r.reasons)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("traces")
    ap.add_argument("--case")
    ap.add_argument("--save-requests", type=pathlib.Path)
    ap.add_argument("--replay", type=pathlib.Path, help="decisions.jsonl from an earlier run: re-decide without the server")
    ap.add_argument("--set", action="append", default=[], help="try a threshold, e.g. --set sift_drop_at=0.1")
    args = ap.parse_args()
    for kv in args.set:  # a changed threshold is a new settings version
        k, v = kv.split("=")
        SETTINGS[k] = float(v)
        SETTINGS["version"] += f"+{k}={v}"
    if args.replay:
        for line in args.replay.read_text().splitlines():
            d = json.loads(line)
            if "answers" in d:
                STORED[(d["case_id"], d["step"], d["question_hash"], d["input_hash"])] = d["answers"]
    rows = []
    for line in pathlib.Path(args.traces).read_text().splitlines():
        t = json.loads(line)
        if args.case and t["case_id"] != args.case:
            continue
        i = t["input"]
        c = Case(t["case_id"], i["received"], i["email"], i["company"], i["documents"], i["bank_country"],
                 i["payment_terms"], i["screening_hits"])
        try:
            r = run_case(c, args.save_requests)
        except LookupError as e:
            print(f"{c.case_id}: not replayed, {e}; run it live")
            continue
        record({"case_id": r.case_id, "step": "outcome", "outcome": r.outcome, "handled_by": r.handled_by,
                "reasons": r.reasons, "matched_hit": r.matched_hit, "missing_documents": r.missing_documents})
        rows.append((t, r))
        print(f"{r.case_id}: {r.outcome:<20} by {r.handled_by:<7} label {t['label']:<20} "
              f"requests {r.vakyn_requests} look-ups {r.lookups} | {'; '.join(r.reasons)}")
    report(rows)
