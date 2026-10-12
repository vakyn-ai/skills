"""Check each field of a structured output against the evidence it cited; send back only the failing
fields; drop what is still unsupported after the last try. pip install typesafe-sdk

Needs TYPESAFE_BASE_URL and TYPESAFE_API_KEY. The agent that fills the fields is stubbed with
AGENT_FIRST and AGENT_RETRY; replace ask_agent() with your own call (same session, so it keeps context).
"""

import datetime
import re

from typesafe_sdk import Choice, TypeSafeClient

LEASE = ("RESIDENTIAL LEASE. Landlord: Ostrava Homes LLC. Tenant: Priya Raman. Premises: Flat 4B, 22 Cedar Row. "
         "Term: 12 months starting 1 November 2026. Rent: $1,850 per month, due on the 1st. "
         "Security deposit: $3,700 (two months' rent). Pets: one cat allowed with written consent; no dogs. "
         "Either party may end the lease after 6 months with 60 days' written notice. "
         "Utilities: tenant pays electricity and internet; landlord pays water.")
MEANING = {  # what each field means, from the output schema's descriptions
    "tenant": "the person who rents the flat",
    "monthly_rent": "the rent per month in dollars",
    "start_date": "the first day of the lease",
    "deposit": "the security deposit in dollars",
    "pets_allowed": "which pets the tenant may keep",
    "break_notice_days": "days of written notice needed to end the lease early",
    "water_paid_by": "who pays for water: tenant or landlord",
    "parking": "parking that comes with the flat",
}
AGENT_FIRST = {  # field: (value, quoted evidence) as the agent returned them
    "tenant": ("Priya Raman", "Tenant: Priya Raman."),
    "monthly_rent": ("1850", "Rent: $1,850 per month, due on the 1st."),
    "start_date": ("2026-11-01", "Term: 12 months starting 1 November 2026."),
    "deposit": ("3700", "Security deposit: $3,700 (two months' rent)."),
    "pets_allowed": ("cats and dogs", "Pets: one cat allowed with written consent; no dogs."),
    "break_notice_days": ("30", "Either party may end the lease after 6 months with 60 days' written notice."),
    "water_paid_by": ("tenant", "Utilities: tenant pays electricity and internet"),
    "parking": ("one space included", "Premises: Flat 4B, 22 Cedar Row."),
}
AGENT_RETRY = {
    "pets_allowed": ("one cat, with written consent; no dogs", "Pets: one cat allowed with written consent; no dogs."),
    "break_notice_days": ("60", "Either party may end the lease after 6 months with 60 days' written notice."),
    "water_paid_by": ("landlord", "Utilities: tenant pays electricity and internet; landlord pays water."),
    "parking": ("one space included", "Premises: Flat 4B, 22 Cedar Row."),
}
VERDICTS = {
    "supported": "The quoted evidence states this value for the field",
    "contradicted": "The quoted evidence states a different value for the field",
    "not_in_evidence": "The quoted evidence does not say what this field's value is",
}
MAX_TRIES = 2          # first answer plus one retry
MIN_CONFIDENCE = 0.8   # starting value; set yours with check

client = TypeSafeClient(timeout=60.0)


def date_check(value, evidence):
    """Exact values are checked in code: a date in the quote either equals the value or it does not."""
    found = [datetime.datetime.strptime(" ".join(m), "%d %B %Y").date()
             for m in re.findall(r"(\d{1,2}) ([A-Z][a-z]+) (\d{4})", evidence)]
    if not found:
        return None  # no date in the quote: let VAKYN judge
    return "supported" if datetime.date.fromisoformat(value) in found else "contradicted"


CODE_CHECKS = {"start_date": date_check}


def ask_agent(fields, attempt, failed):
    """Your agent. On a retry, send only the failing fields and why they failed (failed: {field: verdict})."""
    source = AGENT_FIRST if attempt == 1 else AGENT_RETRY
    return {f: source[f] for f in fields if f in source}


def check(output):
    """One request, one question per field. Returns {field: (verdict, confidence)}."""
    results, asked = {}, {}
    for field, (value, evidence) in output.items():
        if evidence not in LEASE:  # code first: a quote that is not in the source supports nothing
            results[field] = ("not_in_evidence", 1.0)
        elif field in CODE_CHECKS and (verdict := CODE_CHECKS[field](value, evidence)):
            results[field] = (verdict, 1.0)
        else:
            asked[field] = {"meaning": MEANING[field], "value": value, "evidence": evidence}
    if asked:
        questions = {
            f"check_{field}": Choice(
                instructions=f"Does the quoted evidence in state.fields.{field}.evidence support that the lease's "
                             f"{field} ({MEANING[field]}) is state.fields.{field}.value?",
                criteria=VERDICTS)
            for field in asked
        }
        r = client.system_one(state={"fields": asked}, questions=questions)
        for field in asked:
            a = r.choices[f"check_{field}"]
            verdict = a.choice if a.choice in VERDICTS and a.confidence >= MIN_CONFIDENCE else "unsure"
            results[field] = (verdict, round(a.confidence, 2))
    return results


def verified(fields):
    kept, pending, history, failed = {}, list(fields), [], {}
    for attempt in range(1, MAX_TRIES + 1):
        output = ask_agent(pending, attempt, failed)
        results = check(output)
        history.append(results)
        for field, (verdict, conf) in results.items():
            if verdict == "supported":
                kept[field] = output[field][0]
        pending = [f for f in pending if f not in kept]
        failed = {f: results.get(f, ("not returned", 0.0))[0] for f in pending}
        if not pending:
            break
    return kept, pending, history


if __name__ == "__main__":
    kept, dropped, history = verified(list(MEANING))
    for i, results in enumerate(history, 1):
        print(f"try {i}: " + ", ".join(f"{f} {v} {c:.2f}" for f, (v, c) in results.items()))
    print(f"kept: {kept}")
    print(f"dropped (still unsupported after {MAX_TRIES} tries): {dropped}")
