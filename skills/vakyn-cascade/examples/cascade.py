"""Cheap draft, VAKYN check, expensive model only when the draft fails. Side by side first.

pip install typesafe-sdk openai
Needs TYPESAFE_BASE_URL and TYPESAFE_API_KEY (your VAKYN server and key). Outside --demo, also
CHEAP_MODEL and EXPENSIVE_MODEL, plus the key for your chat-model provider (OPENAI_API_KEY, or
CHEAP_API_KEY / EXPENSIVE_API_KEY with CHEAP_BASE_URL / EXPENSIVE_BASE_URL for any
OpenAI-compatible endpoint).

Settings (environment):
  CASCADE_MODE            side_by_side (default): the expensive model answers every request, as
                          today; the cheap draft and VAKYN's verdict are logged next to it.
                          cascade: the cheap draft is sent when VAKYN finds it supported.
  CASCADE_MIN_CONFIDENCE  a draft is accepted only as `supported` at or above this (default 0.8).
  CASCADE_PER_CLAIM_FROM  drafts with this many sentences or more are also checked sentence by
                          sentence (default 4; 0 turns it off).
  CASCADE_LOG             JSON lines log, one line per request (default cascade-log.jsonl).
  CASCADE_REVIEW          review queue for answers that failed twice (default cascade-review.jsonl).

`python cascade.py --demo` runs seven sample questions with canned drafts in place of the chat
models, so it needs no chat-model key. VAKYN's verdicts are real. Without --demo the same questions
go to your chat models. In your app, call answer(question, sources, cheap, expensive) with your
own retrieval.
"""

import datetime
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from typesafe_sdk import Choice, TypeSafeClient

MODE = os.environ.get("CASCADE_MODE", "side_by_side")
MIN_CONFIDENCE = float(os.environ.get("CASCADE_MIN_CONFIDENCE", "0.8"))  # starting value; set yours with vakyn-check
PER_CLAIM_FROM = int(os.environ.get("CASCADE_PER_CLAIM_FROM", "4"))
LOG_PATH = os.environ.get("CASCADE_LOG", "cascade-log.jsonl")
REVIEW_PATH = os.environ.get("CASCADE_REVIEW", "cascade-review.jsonl")
DEMO = "--demo" in sys.argv
CHEAP_MODEL = "demo-cheap" if DEMO else os.environ["CHEAP_MODEL"]
EXPENSIVE_MODEL = "demo-expensive" if DEMO else os.environ["EXPENSIVE_MODEL"]
SOURCE_BUDGET_TOKENS = 24_000  # sources share the 32,768-token state with the question, draft and claims

DRAFT_PROMPT = (
    "Answer the customer's question using only the help articles below. If they do not contain "
    "the answer, say you could not find it and that a person will follow up. Do not add facts."
)
DECLINE = "I could not find this in our help articles. A member of our team will reply to you."
HOLD = "Thanks, a member of our team will check this and reply to you."

VERDICT = {
    "supported": "Every sentence in the draft is stated in the sources, and the draft answers the question",
    "unsupported": "At least one sentence in the draft states something the sources do not say or say "
                   "differently: a number, a date, a step, a promise",
    "cannot_answer_from_sources": "The sources do not contain the answer to the question, whatever the draft says",
    "off_topic": "The draft does not answer the question that was asked",
}
CLAIM = {
    "supported": "The sources state this sentence",
    "contradicted": "The sources state something that makes this sentence false",
    "not_in_sources": "The sources do not say enough to back or refute this sentence",
}
MATCH = {  # side by side only: the cheap draft against the expensive answer (agreement, not accuracy)
    "same_answer": "The draft gives the same answer with the same facts, numbers and steps as the reference; wording may differ",
    "draft_incomplete": "The draft gives the same answer but leaves out a fact or step that the reference gives",
    "different_answer": "The draft gives a different answer, or a different fact, number or step, than the reference",
    "cannot_compare": "The draft or the reference does not answer the question",
}

LOG_FIELDS = [  # the shared side-by-side fields first, then the cascade's own
    "ts", "request_id", "question", "vakyn_pick", "vakyn_confidence", "vakyn_probabilities",
    "chat_pick", "agree", "mode", "used", "route", "escalated", "claims", "expensive_check",
    "cheap_model", "expensive_model", "tokens", "ms", "label", "texts",
]

vakyn = TypeSafeClient(timeout=60.0)


def trim_sources(sources, budget=SOURCE_BUDGET_TOKENS):
    """Keep sources in retrieval order while they fit (about 4 characters per token)."""
    kept, used = [], 0
    for s in sources:
        size = len(json.dumps(s)) // 4 + 1
        if used + size > budget:
            break
        kept.append(s)
        used += size
    return kept


def split_claims(draft):
    """Sentences, with short ones ("Yes.", "Sure!") joined to the next: alone they state nothing."""
    parts = [p for p in re.split(r"(?<=[.!?])\s+", draft.strip()) if p]
    claims, carry = [], ""
    for p in parts:
        p = f"{carry} {p}".strip()
        if len(p.split()) < 4:
            carry = p
        else:
            claims.append(p)
            carry = ""
    if carry:
        claims.append(carry)
    return claims


def check(question, sources, draft):
    """VAKYN's verdict on a draft. Long drafts also get one question per sentence, in the same request."""
    state = {"question": question, "sources": sources, "draft": draft}
    questions = {"verdict": Choice(
        instructions="Is the draft answer in state.draft backed by state.sources, as an answer to state.question?",
        criteria=VERDICT)}
    claims = split_claims(draft) if PER_CLAIM_FROM else []
    if len(claims) >= PER_CLAIM_FROM > 0:
        state["claims"] = {f"c{i + 1}": c for i, c in enumerate(claims)}
        for key in state["claims"]:
            questions[key] = Choice(
                instructions=f"Is the sentence in state.claims.{key} backed by state.sources?", criteria=CLAIM)
    result = vakyn.system_one(state=state, questions=questions)
    v = result.choices["verdict"]
    if v.choice not in VERDICT:  # code checks the pick is an offered option
        raise ValueError(f"unexpected verdict {v.choice}")
    out = {"pick": v.choice, "confidence": v.confidence, "probabilities": dict(v.probabilities),
           "request_id": result.request_id, "claims": None}
    if "claims" in state:
        out["claims"] = [{"text": text, "pick": result.choices[k].choice,
                          "confidence": result.choices[k].confidence}
                         for k, text in state["claims"].items()]
    return out


def accepted(v):
    """Send a draft only when the verdict and every checked sentence are `supported` above the bar."""
    ok = v["pick"] == "supported" and v["confidence"] >= MIN_CONFIDENCE
    return ok and all(c["pick"] == "supported" and c["confidence"] >= MIN_CONFIDENCE for c in v["claims"] or [])


def compare(question, draft, reference):
    result = vakyn.system_one(
        state={"question": question, "reference_answer": reference, "draft": draft},
        questions={"match": Choice(
            instructions="Compared with the reference answer in state.reference_answer, "
                         "how does the draft in state.draft answer state.question?",
            criteria=MATCH)})
    return result.choices["match"].choice


# --- chat models -------------------------------------------------------------------------------

def make_drafter(model, base_url_env, key_env):
    if DEMO:
        return lambda question, sources: demo_draft(model, question, sources)
    from openai import OpenAI
    client = OpenAI(base_url=os.environ.get(base_url_env), api_key=os.environ.get(key_env) or os.environ.get("OPENAI_API_KEY"))

    def draft(question, sources):
        r = client.chat.completions.create(model=model, messages=[
            {"role": "system", "content": DRAFT_PROMPT},
            {"role": "user", "content": json.dumps({"help_articles": sources, "question": question})},
        ])
        usage = {"in": r.usage.prompt_tokens, "out": r.usage.completion_tokens} if r.usage else None
        return r.choices[0].message.content, usage
    return draft


def timed(fn, *args):
    t = time.perf_counter()
    out = fn(*args)
    return out, round((time.perf_counter() - t) * 1000)


# --- the cascade -------------------------------------------------------------------------------

def answer(question, sources, cheap, expensive):
    """Returns the text to send. Writes one log line."""
    sources = trim_sources(sources)
    line = {"mode": MODE, "cheap_model": CHEAP_MODEL, "expensive_model": EXPENSIVE_MODEL,
            "tokens": {"cheap": None, "expensive": None}, "ms": {}, "chat_pick": None, "agree": None,
            "expensive_check": None, "label": None, "texts": {"question": question}}

    with ThreadPoolExecutor(2) as pool:
        exp_future = pool.submit(timed, expensive, question, sources) if MODE == "side_by_side" else None
        (draft, line["tokens"]["cheap"]), line["ms"]["cheap"] = timed(cheap, question, sources)
        line["texts"]["cheap_draft"] = draft
        try:
            v, line["ms"]["check"] = timed(check, question, sources, draft)
        except Exception as err:  # VAKYN down or a bad answer: behave as today, the expensive model answers
            print(f"VAKYN unavailable: {err}", file=sys.stderr)
            v = None
        if exp_future:
            (exp_text, line["tokens"]["expensive"]), line["ms"]["expensive"] = exp_future.result()

    if v is None:
        route = "escalate"
    elif accepted(v):
        route = "accept_cheap"
    elif v["pick"] == "cannot_answer_from_sources" and v["confidence"] >= MIN_CONFIDENCE:
        route = "decline"  # the sources lack the answer: a bigger model has the same sources
    else:
        route = "escalate"
    line.update({"request_id": v and v["request_id"], "question": "draft_check",
                 "vakyn_pick": v and v["pick"], "vakyn_confidence": v and v["confidence"],
                 "vakyn_probabilities": v and v["probabilities"], "claims": v and v["claims"],
                 "route": route, "escalated": route == "escalate"})

    if MODE == "side_by_side":
        # The person's customers get the expensive answer, as today. Compare the cheap draft with it.
        line["texts"]["expensive_answer"] = exp_text
        try:
            line["chat_pick"] = compare(question, draft, exp_text)
            line["agree"] = (route == "accept_cheap") == (line["chat_pick"] == "same_answer")
        except Exception as err:
            print(f"VAKYN compare failed: {err}", file=sys.stderr)
        line["used"], reply = "expensive", exp_text
    elif route == "accept_cheap":
        line["used"], reply = "cheap", draft
    elif route == "decline":
        line["used"], reply = "decline", DECLINE
    else:  # escalate once; never loop
        (exp_text, line["tokens"]["expensive"]), line["ms"]["expensive"] = timed(expensive, question, sources)
        line["texts"]["expensive_answer"] = exp_text
        try:
            v2, line["ms"]["check2"] = timed(check, question, sources, exp_text)
            line["expensive_check"] = {"pick": v2["pick"], "confidence": v2["confidence"],
                                       "request_id": v2["request_id"]}
            ok = accepted(v2)
        except Exception as err:  # VAKYN down: send the expensive answer unchecked, as before the cascade
            print(f"VAKYN unavailable: {err}", file=sys.stderr)
            ok = True
        if ok:
            line["used"], reply = "expensive", exp_text
        else:  # failed twice: a person decides
            line["used"], reply = "person", HOLD
            with open(REVIEW_PATH, "a") as f:
                f.write(json.dumps({"question": question, "sources": sources, "cheap_draft": draft,
                                    "expensive_answer": exp_text, "verdicts": [v, line["expensive_check"]]}) + "\n")

    line["ts"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    line = {k: line.get(k) for k in LOG_FIELDS}
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(line) + "\n")
    return reply, line


# --- demo: canned drafts in place of the chat models ------------------------------------------

KB = {
    "kb-112": "Refunds for annual plans. If you cancel an annual Tallyfox plan within 14 days of the purchase date, "
              "we refund the full amount to the card used for the purchase. After 14 days, annual plans are not "
              "refunded; the plan stays active until the end of the paid year. Monthly plans are never refunded. "
              "To ask for a refund, open Settings > Billing and choose Cancel plan.",
    "kb-087": "Changing your plan. You can switch from monthly to annual billing at any time in Settings > Billing. "
              "The unused part of the current month is credited to the annual price. Switching from annual to "
              "monthly takes effect at the end of the paid year.",
    "kb-140": "Plans and users. Starter includes up to 3 users. Team includes up to 15 users. Business has no user limit.",
    "kb-201": "Exporting invoices. Open Reports > Invoices, pick a date range and choose Export. You can export as CSV "
              "or PDF. Exports with more than 500 invoices are emailed to you as a download link.",
    "kb-160": "Downgrading. When you move from Team to Starter, all your invoices and clients stay. Users beyond the "
              "Starter limit lose access at the end of the billing period; the account owner chooses who stays.",
    "kb-175": "Invoice languages. Invoices can be issued in English, French or German. Set the language per client "
              "under Clients > Edit > Invoice language.",
}
DEMO_CASES = [  # question, source ids, cheap draft, expensive answer
    ("I bought the annual plan last week by mistake. Can I get my money back?", ["kb-112", "kb-087"],
     "Yes. You are within 14 days of buying it, so cancel in Settings > Billing (Cancel plan) and the full amount goes back to your card.",
     "Yes. Annual plans cancelled within 14 days of purchase are refunded in full to the card you paid with. Open Settings > Billing and choose Cancel plan."),
    ("How many people can use our account on the Starter plan?", ["kb-140"],
     "The Starter plan includes up to 5 users.",
     "Starter includes up to 3 users. For more, Team allows up to 15 and Business has no limit."),
    ("Can I pay my subscription by bank transfer instead of card?", ["kb-112", "kb-087"],
     "Yes, you can pay by bank transfer. Choose Bank transfer in Settings > Billing and use the reference shown there.",
     "I could not find payment by bank transfer in our help articles. A member of our team will reply to you."),
    ("How do I export all my invoices from last year?", ["kb-201"],
     "Go to Reports > Invoices, pick last year as the date range and choose Export.",
     "Open Reports > Invoices, set the date range to last year and choose Export, as CSV or PDF. If there are more than 500 invoices, you get the download link by email."),
    ("What happens to my invoices if we downgrade from Team to Starter?", ["kb-160", "kb-140"],
     "Starter includes up to 3 users, Team up to 15.",
     "Nothing happens to them: all invoices and clients stay when you move from Team to Starter. Only users beyond 3 lose access, at the end of the billing period."),
    ("We are on monthly billing. How do we switch to annual and what happens to this month?", ["kb-087"],
     "You can switch to annual billing at any time. Open Settings > Billing and choose annual. The unused part of this month is credited to the annual price. You also get 10% off the annual price when you switch. The change applies right away.",
     "Open Settings > Billing and switch to annual billing; you can do it at any time. The unused part of the current month is credited to the annual price."),
    ("Can I send invoices to my clients in Spanish?", ["kb-175"],
     "Yes. Set Spanish as the invoice language for each client under Clients > Edit > Invoice language.",
     "Yes, Spanish is supported: choose it per client under Clients > Edit > Invoice language."),
]
DEMO_TEXT = {(q, m): t for q, _, c, e in DEMO_CASES for m, t in (("demo-cheap", c), ("demo-expensive", e))}


def demo_draft(model, question, sources):
    text = DEMO_TEXT[(question, model)]
    prompt = DRAFT_PROMPT + json.dumps({"help_articles": sources, "question": question})
    return text, {"in": len(prompt) // 4, "out": len(text) // 4}  # estimates; real runs log the provider's usage


if __name__ == "__main__":
    cheap = make_drafter(CHEAP_MODEL, "CHEAP_BASE_URL", "CHEAP_API_KEY")
    expensive = make_drafter(EXPENSIVE_MODEL, "EXPENSIVE_BASE_URL", "EXPENSIVE_API_KEY")
    for question, ids, _, _ in DEMO_CASES:  # without --demo, the same questions go to your chat models
        sources = [{"id": i, "text": KB[i]} for i in ids]  # your retrieval goes here
        reply, line = answer(question, sources, cheap, expensive)
        claims = "".join(f"\n    sentence {c['pick']:15} {c['confidence']:.2f}  {c['text']}" for c in line["claims"] or [])
        print(f"{question}\n  {line['vakyn_pick']} {line['vakyn_confidence']} -> {line['route']}, used {line['used']}"
              f"{', vs expensive: ' + str(line['chat_pick']) if line['chat_pick'] else ''}{claims}")
    print(f"log: {LOG_PATH}")
