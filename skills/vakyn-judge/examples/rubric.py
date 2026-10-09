"""The support-reply rubric as data, plus the code that turns answers into a verdict.

One place for the criteria, shared by judge.py, align.py, test_replies.py and vakyn_assert.py.
Each criterion is one VAKYN question. Must-pass gates, weights and thresholds stay in code.
"""

TASK = "Reply to a customer of a weekly meal-kit delivery service."
RULES = [
    "A missing or damaged box reported within 48 hours of delivery gets a full credit or a free replacement box, the customer's pick.",
    "A missing or damaged box reported later than 48 hours after delivery gets a 50% credit.",
    "Credits and replacement boxes are the only remedies; never refund money to the card.",
    "Skipping or pausing a week is free when done before Wednesday 23:59 for the next week's box.",
    "Never ask the customer for a password, a full card number or a card security code.",
    "Do not promise a delivery hour; give the delivery day and the 8:00-20:00 window.",
]

# name -> question. "pass_when" is the noul answer that means the criterion passed.
CRITERIA = {
    "answers_request": {
        "type": "noul", "must_pass": True, "weight": 0.3, "pass_when": True,
        "instructions": "Does state.output deal with the main thing the customer asks for in state.input?",
        "criteria": {
            "true": "The reply works on the customer's main request, even if it says no or goes about it in a way another criterion fails",
            "false": "The reply ignores the main request, answers a different one, or only says the message was received",
        },
    },
    "follows_rules": {
        "type": "noul", "must_pass": True, "weight": 0.3, "pass_when": True,
        "instructions": "Is everything state.output commits to allowed by state.rules?",
        "criteria": {
            "true": "Each offer, promise and request in the reply is allowed by state.rules; a reply that offers nothing breaks no rule",
            "false": "The reply offers, promises or asks for something a rule in state.rules does not allow",
        },
    },
    "asks_for_secret": {
        "type": "noul", "must_pass": True, "weight": 0.0, "pass_when": False,
        "instructions": "Does state.output ask the customer to share a secret (a password, a full card number, a card security code)?",
        "criteria": {
            "true": "The reply asks the customer to send or type a password, full card number or security code",
            "false": "The reply asks for no secret; an order number, email address or last four card digits are not secrets",
        },
    },
    "next_step": {
        "type": "noul", "must_pass": False, "weight": 0.2, "pass_when": True,
        "instructions": "Does state.output give the customer a concrete next step?",
        "criteria": {
            "true": "Says what the customer can do now, or what the team will do and by when",
            "false": "Leaves the customer waiting with no action, no owner and no time, such as 'we are looking into it'",
        },
    },
    "tone": {
        "type": "score", "must_pass": False, "weight": 0.2, "pass_at": 1.0,
        "instructions": "How does the tone of state.output come across to the customer in state.input?",
        "criteria": [
            "Rude, cold or blaming the customer",
            "Neutral but stiff, reads like a template",
            "Friendly and polite",
            "Warm and personal while staying brief",
        ],
    },
}

# The first draft, before alignment with the support leads' labels (see align.py and
# references/alignment.md): what changed is the wording of three criteria, not a threshold.
FIRST_DRAFT = {
    "answers_request": {
        **CRITERIA["answers_request"],
        "criteria": {
            "true": "The reply handles the customer's main request, even if the answer is no",
            "false": "The reply ignores the main request, answers a different one, or only acknowledges it",
        },
    },
    "follows_rules": {
        **CRITERIA["follows_rules"],
        "instructions": "Does state.output stay within every rule in state.rules?",
        "criteria": {
            "true": "Everything the reply offers, promises or refuses matches state.rules",
            "false": "The reply offers, promises or refuses something that breaks a rule in state.rules",
        },
    },
    "next_step": {
        **CRITERIA["next_step"],
        "instructions": "Does state.output say what happens next?",
        "criteria": None,
    },
}

# Starting values (vakyn-check skill, thresholds page). Set yours from labeled replies.
NOUL_YES = 0.8   # pass-side probability at or above this: the criterion passes
NOUL_NO = 0.2    # at or below this: it fails; in between: unsure, a person grades it
PASS_SCORE = 0.7  # weighted score needed for an overall pass


def criteria_for(draft="aligned"):
    return {**CRITERIA, **FIRST_DRAFT} if draft == "first" else CRITERIA


def build_state(item):
    """Evidence only: the task, the customer's message, the reply being graded, the rules."""
    return {"task": TASK, "input": item["input"], "output": item["output"], "rules": item.get("rules", RULES)}


def request_body(item, criteria=CRITERIA):
    """The raw JSON body for POST /v1/systemone: one output, every criterion, one request."""
    qs = {}
    for name, c in criteria.items():
        q = {"type": c["type"], "instructions": c["instructions"]}
        if c.get("criteria"):
            q["criteria"] = c["criteria"]
        qs[name] = q
    return {"model": "jev-latest", "state": build_state(item), "questions": qs}


def criterion_results(answers, criteria=CRITERIA):
    """answers: {name: {"noul": p} or {"score": s, "confidence": c}} -> per-criterion result."""
    out = {}
    for name, c in criteria.items():
        a = answers[name]
        if c["type"] == "noul":
            p_pass = a["noul"] if c["pass_when"] else 1 - a["noul"]
            verdict = "pass" if p_pass >= NOUL_YES else "fail" if p_pass <= NOUL_NO else "unsure"
            out[name] = {"verdict": verdict, "p_pass": round(p_pass, 3), "value": round(p_pass, 3)}
        else:
            top = len(c["criteria"]) - 1
            verdict = "pass" if a["score"] >= c["pass_at"] else "fail"
            out[name] = {"verdict": verdict, "score": round(a["score"], 2), "confidence": round(a["confidence"], 2),
                         "value": round(a["score"] / top, 3)}
    return out


def overall(results, criteria=CRITERIA):
    """Verdict in code: every must-pass criterion passes, and the weighted score clears PASS_SCORE."""
    weighted = sum(c["weight"] * results[n]["value"] for n, c in criteria.items())
    must = [n for n, c in criteria.items() if c["must_pass"]]
    failed = [n for n in must if results[n]["verdict"] == "fail"]
    unsure = [n for n in must if results[n]["verdict"] == "unsure"]
    if failed:
        verdict = "fail"
    elif unsure:
        verdict = "review"  # a person decides; never count unsure as a pass
    else:
        verdict = "pass" if weighted >= PASS_SCORE else "fail"
    return {"verdict": verdict, "weighted": round(weighted, 3), "failed": failed, "unsure": unsure}


def answers_from_response(r, criteria=CRITERIA):
    """SDK response -> plain dict, the same shape as the stored answers file."""
    out = {}
    for name, c in criteria.items():
        if c["type"] == "noul":
            out[name] = {"noul": r.nouls[name].noul}
        else:
            s = r.scores[name]
            out[name] = {"score": s.score, "confidence": s.confidence}
    return out
