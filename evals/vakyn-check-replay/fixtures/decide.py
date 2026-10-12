"""Warranty claim decision code, policy warranty-v4. VAKYN answers what the damage is; this decides what happens."""

APPROVE_AT = 0.85   # defect_type confidence needed to approve or reject automatically
PHOTO_AT = 0.8      # photo_shows_damage noul needed to approve


def decide(answers, claim):
    d = answers["defect_type"]
    photo = answers["photo_shows_damage"]["noul"]
    if d["choice"] == "accident" and d["confidence"] >= APPROVE_AT:
        return "reject"
    if d["choice"] == "manufacturing" and d["confidence"] >= APPROVE_AT and photo >= PHOTO_AT:
        return "approve"
    return "person"
