"""Pick instead of generate: code finds the candidates, VAKYN picks one, code copies it exactly.

Two uses: the amount and due date in an email, and the role of each line in pasted text.
pip install typesafe-sdk. Needs TYPESAFE_BASE_URL and TYPESAFE_API_KEY.
"""

import re

from typesafe_sdk import Choice, TypeSafeClient

MIN_CONFIDENCE = 0.7  # starting value; set yours with check
client = TypeSafeClient(timeout=30.0)

AMOUNT_RE = re.compile(r"€\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?")
DATE_RE = re.compile(r"\b\d{1,2} (?:January|February|March|April|May|June|July|August|September|October|November|December)\b")


def candidates(text: str, pattern: re.Pattern) -> dict[str, dict]:
    """Every match with the sentence it sits in. Ids come from the value, never from the position."""
    found = {}
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        for m in pattern.finditer(sentence):
            key = re.sub(r"[^a-z0-9]+", "_", m.group(0).lower().replace("€", "eur ")).strip("_")
            found.setdefault(key, {"value": m.group(0), "sentence": sentence.strip()})
    return found


def pick(text: str, field: str, question: str, cands: dict[str, dict]) -> str | None:
    options = {k: f'{c["value"]}, in: "{c["sentence"]}"' for k, c in cands.items()}
    options["none_of_these"] = f"None of these is the {field}, or the text does not say"
    r = client.system_one(state={"supplier_email": text}, questions={field: Choice(instructions=question, criteria=options)})
    a = r.choices[field]
    if a.choice not in cands or a.confidence < MIN_CONFIDENCE:
        return None  # none_of_these or unsure: a person fills the field
    return cands[a.choice]["value"]  # copied from the text by code, character for character


def payment_due(email: str) -> dict:
    return {
        "amount": pick(email, "amount_due", "Which amount in the supplier's email is the amount the customer "
                       "still has to pay now?", candidates(email, AMOUNT_RE)),
        "due_date": pick(email, "due_date", "Which date in the supplier's email is the date the remaining "
                         "payment is due?", candidates(email, DATE_RE)),
    }


LINE_ROLES = {
    "heading": {"is": "a title for the lines that follow",
                "looks like": "short, no final period, followed by text or a list about it"},
    "list_item": {"is": "one entry in a list of similar short items",
                  "looks like": "a noun phrase, next to lines of the same kind"},
    "paragraph": {"is": "running text", "looks like": "one or more full sentences ending with a period"},
    "other": {"is": "something that is not content", "includes": ["page numbers", "signatures", "stray symbols"]},
}


def recover_structure(pasted: str) -> str:
    """Rebuild Markdown from text that lost its formatting. The words are never rewritten."""
    lines = [line.strip() for line in pasted.splitlines() if line.strip()]
    questions = {f"line_{i}": Choice(instructions=f'In the pasted text, what is the line "{line}"?', criteria=LINE_ROLES)
                 for i, line in enumerate(lines, 1)}
    r = client.system_one(state={"pasted_text": "\n".join(lines)}, questions=questions)
    out = []
    for i, line in enumerate(lines, 1):
        a = r.choices[f"line_{i}"]
        role = a.choice if a.choice in LINE_ROLES and a.confidence >= MIN_CONFIDENCE else "paragraph"  # safe default
        if role == "heading":
            out.append(f"\n## {line}")
        elif role == "list_item":
            out.append(f"- {line}")
        elif role == "paragraph":
            out.append(f"\n{line}")
        # other (page numbers, stray symbols) is dropped
    return "\n".join(out).strip()


EMAIL = ("Hi Dana, thanks for the €300 deposit we received on 2 October. The remaining balance of €1,240.50 "
         "is due by 14 November. Payments after that date add a €25 late fee. Best, Marco")
print(payment_due(EMAIL))
print(recover_structure("""Trail Kettle 1.2
A light steel kettle for camping trips. It boils a liter in four minutes on a gas stove.
What's in the box
Kettle with folding handle
Mesh carry bag
Care guide
Care
Rinse after each use and let it dry with the lid open.
Page 2 of 3"""))
