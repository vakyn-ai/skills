"""Pre-send checklist for VAKYN requests, as code.

Mirrors the checklist the skills teach (skills/get-started/references/checklist.md). Used by the
repo's tests only; the plugin itself ships no scripts.
"""

import json
import re

TYPES = {"noul", "choice", "score"}
ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
ESCAPE_WORDS = ("none", "other", "unknown", "unclear", "not_enough", "ask_user", "needs_", "no_match", "no_good", "cannot", "not_in_", "neither", "not_")
POSITIONAL_RE = re.compile(r"\b(option|item|candidate|choice)\s+\d+\b|\bthe (first|second|third|last) (option|item|one)\b", re.I)
# Rough token estimate: ~3.5 characters per token for English JSON.
CHARS_PER_TOKEN = 3.5
MAX_STATE_PLUS_QUESTION = 32_768
MAX_TOTAL = 65_536


NUMBER_RE = re.compile(r"\s*\d+(\.\d+)?\s*")


def described(v):
    """True when v says something in words: a non-blank string, or an object or list that holds one.

    The server renders objects as `key: value` lines and lists as `- item` lines, so structured
    instructions, option descriptions and score levels are fine as long as they are not empty.
    """
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, dict):
        return any(described(x) for x in v.values())
    if isinstance(v, list):
        return any(described(x) for x in v)
    return False


def bare_number(v):
    """A level written as a number ("3" or 3) gives the model nothing to compare against."""
    if isinstance(v, bool):
        return False
    return isinstance(v, (int, float)) or (isinstance(v, str) and NUMBER_RE.fullmatch(v) is not None)


def text_of(v):
    """All the words in a string, object or list, for the wording checks."""
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        return "\n".join(f"{k}: {text_of(x)}" for k, x in v.items())
    if isinstance(v, list):
        return "\n".join(text_of(x) for x in v)
    return "" if v is None else str(v)


def tokens(obj):
    text = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    return int(len(text) / CHARS_PER_TOKEN) + 1


def check(req):
    """Return (errors, warnings) for one request body."""
    errors, warnings = [], []
    if not isinstance(req, dict):
        return ["request is not a JSON object"], warnings
    extra = set(req) - {"model", "state", "questions"}
    if extra:
        errors.append(f"unknown top-level fields: {sorted(extra)}")
    if not isinstance(req.get("model"), str) or not req.get("model"):
        errors.append("model must be a non-empty string")
    if "state" not in req or req["state"] is None:
        errors.append("state is required and cannot be null")
    elif not isinstance(req["state"], (str, dict, list)):
        errors.append("state must be a string, object or array")
    qs = req.get("questions")
    if not isinstance(qs, dict) or not qs:
        errors.append("questions must be a non-empty object")
        return errors, warnings

    state_tokens = tokens(req.get("state", ""))
    longest = 0
    for qid, q in qs.items():
        where = f"questions.{qid}"
        if not ID_RE.match(qid):
            warnings.append(f"{where}: use a snake_case name, so answers are read by name")
        if not isinstance(q, dict):
            errors.append(f"{where}: must be an object")
            continue
        extra = set(q) - {"type", "instructions", "criteria"}
        if extra:
            errors.append(f"{where}: unknown fields {sorted(extra)}")
        t = q.get("type")
        if t not in TYPES:
            errors.append(f"{where}: type must be one of noul, choice, score")
            continue
        raw = q.get("instructions")
        if not described(raw):
            errors.append(f"{where}: instructions must be a non-empty string, object or list")
        ins = text_of(raw)
        if POSITIONAL_RE.search(ins):
            warnings.append(f"{where}: refers to options by position; name them instead")
        c = q.get("criteria")
        if t == "choice":
            if not isinstance(c, dict):
                errors.append(f"{where}: choice needs criteria as an object of options")
            else:
                if len(c) < 2 or len(c) > 255:
                    errors.append(f"{where}: choice needs 2 to 255 options, has {len(c)}")
                for k, v in c.items():
                    if not described(v):
                        errors.append(f"{where}.criteria.{k}: give every option a description (text, object or list)")
                if not any(any(w in k.lower() for w in ESCAPE_WORDS) for k in c):
                    warnings.append(f"{where}: no escape option (none / other / not enough evidence)")
        elif t == "score":
            if not isinstance(c, list):
                errors.append(f"{where}: score needs criteria as an ordered list, lowest first")
            else:
                if len(c) < 2 or len(c) > 10:
                    errors.append(f"{where}: score needs 2 to 10 levels, has {len(c)}")
                for i, v in enumerate(c):
                    if bare_number(v):
                        errors.append(f"{where}.criteria[{i}]: a bare number is not a level; describe it")
                    elif not described(v):
                        errors.append(f"{where}.criteria[{i}]: describe every level in words")
        else:  # noul
            if c is not None:
                if not isinstance(c, dict) or not set(c) <= {"true", "false"} or not c:
                    errors.append(f"{where}: noul criteria may only have the keys true and false")
            # Only plain-string questions: structured instructions list includes and contrasts with "and".
            if isinstance(raw, str) and re.search(r"\b(and|or)\b", ins) and ins.count("?") <= 1 and len(ins) < 160:
                warnings.append(f"{where}: noul may hold two propositions (and/or); ask one thing")
        longest = max(longest, tokens(q))

    if state_tokens + longest > MAX_STATE_PLUS_QUESTION:
        errors.append(f"state plus longest question ~{state_tokens + longest} tokens > {MAX_STATE_PLUS_QUESTION}")
    if state_tokens + tokens(qs) > MAX_TOTAL:
        errors.append(f"state plus all questions ~{state_tokens + tokens(qs)} tokens > {MAX_TOTAL}")
    return errors, warnings
