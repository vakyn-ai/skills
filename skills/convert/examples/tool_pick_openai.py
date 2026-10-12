"""Tool pick with VAKYN in an OpenAI SDK app: pick-then-fill, side by side first.

pip install typesafe-sdk openai
Needs TYPESAFE_BASE_URL and TYPESAFE_API_KEY (your VAKYN server and key) and OPENAI_API_KEY.

Settings (environment):
  VAKYN_TOOL_MODE            side_by_side (default): the chat model still picks and acts; both picks
                             are logged. vakyn: VAKYN picks, the chat model only fills arguments.
  VAKYN_TOOL_MIN_CONFIDENCE  in vakyn mode, picks below this go to the chat model (default 0.8).
  VAKYN_TOOL_LOG             JSON lines log of every pick (default vakyn-tool-picks.jsonl).

Run `python tool_pick_openai.py --dry` to see VAKYN's picks for three sample turns without a
chat-model key (the chat model is skipped and chat_pick is logged as null).
"""

import datetime
import json
import os
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor

from typesafe_sdk import Choice, TypeSafeClient

MODE = os.environ.get("VAKYN_TOOL_MODE", "side_by_side")
MIN_CONFIDENCE = float(os.environ.get("VAKYN_TOOL_MIN_CONFIDENCE", "0.8"))  # starting value; set yours with check
LOG_PATH = os.environ.get("VAKYN_TOOL_LOG", "vakyn-tool-picks.jsonl")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "gpt-4.1-mini")
DRY = "--dry" in sys.argv

# Your app's existing tool list, unchanged. Here: the sample list next to this file.
TOOLS = json.loads(pathlib.Path(__file__).with_name("support-tools.openai.json").read_text())
TOOLS_BY_NAME = {t["function"]["name"]: t for t in TOOLS}

# One option per tool: name -> one line. Written from each tool's description, with the boundary
# between look-alike tools made explicit. Parameter schemas are never sent to VAKYN.
OPTIONS = {
    "search_help_center": "Find a help-center article that explains how a feature works",
    "get_invoice": "Fetch an invoice, its charges and payment status, when they are not known yet",
    "refund_charge": "Refund a card charge, once the customer asked for money back and the charge is known",
    "send_password_reset": "Email a password reset link when the customer cannot sign in",
    "file_bug_report": "Report a product problem to engineering, once the customer has said what is broken",
    "handoff_to_agent": "Hand the conversation to a person: the customer asks for one or is upset",
    "none": "No tool is needed now: answer the customer directly",
    "ask_user": "The request does not say what is wrong or what is wanted (\"it doesn't work\"); ask the customer first",
}
assert set(OPTIONS) - {"none", "ask_user"} == set(TOOLS_BY_NAME), "every tool needs exactly one option"

INSTRUCTIONS = (
    "Which tool should the support assistant call next to handle state.user_request? "
    "Use state.last_tool_result: a tool already called does not need to be called again."
)

vakyn = TypeSafeClient(timeout=30.0)
chat = None if DRY else __import__("openai").OpenAI()


def build_state(messages):
    """Goal, recent turns and the last tool result. User text stays data under its own keys."""
    turns = [m for m in messages if m["role"] in ("user", "assistant") and m.get("content")]
    users = [m for m in turns if m["role"] == "user"]
    called = [c["function"]["name"] for m in messages for c in (m.get("tool_calls") or [])]
    tool_msgs = [m for m in messages if m["role"] == "tool"]
    return {
        "assistant": "Support assistant for Lumen, a reporting app. It calls one tool at a time.",
        "user_request": users[-1]["content"] if users else "",
        "recent_turns": [{"role": m["role"], "text": m["content"][:2000]} for m in turns[-6:]],
        "tools_already_called": called,
        "last_tool_result": tool_msgs[-1]["content"][:8000] if tool_msgs else "none yet",
    }


def vakyn_pick(messages):
    """VAKYN's pick, or None when the server cannot answer (the chat model then picks)."""
    try:
        result = vakyn.system_one(
            state=build_state(messages),
            questions={"next_tool": Choice(instructions=INSTRUCTIONS, criteria=OPTIONS)},
        )
    except Exception as err:  # unreachable, timeout, 4xx: never block the app on VAKYN
        print(f"VAKYN unavailable: {err}", file=sys.stderr)
        return None
    answer = result.choices["next_tool"]
    if answer.choice not in OPTIONS:  # code checks the pick is an offered option
        return None
    return {"pick": answer.choice, "confidence": answer.confidence,
            "probabilities": dict(answer.probabilities), "request_id": result.request_id}


def chat_call(messages, tools=None, tool_choice=None):
    """One chat-model call. tools=None means plain text, no tool."""
    if DRY:
        return None
    kwargs = {"model": CHAT_MODEL, "messages": messages}
    if tools:
        kwargs.update(tools=tools, tool_choice=tool_choice or "auto")
    return chat.chat.completions.create(**kwargs).choices[0].message


def picked_tool(message):
    if message is None:
        return None
    return message.tool_calls[0].function.name if message.tool_calls else "none"


def log(entry):
    entry = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(), **entry}
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def next_step(messages):
    """Returns the assistant message to act on: a tool call or a text reply."""
    if MODE == "side_by_side":
        # Both pick at once, so VAKYN adds no wait. The chat model's message is used, as before.
        with ThreadPoolExecutor(2) as pool:
            v_future = pool.submit(vakyn_pick, messages)
            message = chat_call(messages, TOOLS, "auto")
            v = v_future.result()
        used = "chat"
    else:
        v = vakyn_pick(messages)
        if v is None or v["confidence"] < MIN_CONFIDENCE:
            message, used = chat_call(messages, TOOLS, "auto"), "chat"  # unsure: the chat model picks
        elif v["pick"] == "none":
            message, used = chat_call(messages), "vakyn"  # reply in words, no tool
        elif v["pick"] == "ask_user":
            note = {"role": "system", "content": "Ask the customer one short question to learn what they need."}
            message, used = chat_call(messages + [note]), "vakyn"
        else:  # pick-then-fill: offer only the picked tool and force it
            forced = {"type": "function", "function": {"name": v["pick"]}}
            message, used = chat_call(messages, [TOOLS_BY_NAME[v["pick"]]], forced), "vakyn"

    chat_pick = picked_tool(message) if used == "chat" else None
    log({
        "request_id": v and v["request_id"],
        "mode": MODE,
        "vakyn_pick": v and v["pick"],
        "vakyn_confidence": v and v["confidence"],
        "vakyn_probabilities": v and v["probabilities"],
        "chat_pick": chat_pick,
        "agree": None if v is None or chat_pick is None else v["pick"] == chat_pick,
        "used": used,
    })
    return message, v


if __name__ == "__main__":
    samples = [
        [{"role": "user", "content": "How do I schedule a dashboard to be emailed every Monday?"}],
        [{"role": "user", "content": "I lost access, the login page says my password is wrong."}],
        [{"role": "user", "content": "it doesnt work again"}],
    ]
    for messages in samples:
        message, v = next_step(messages)
        shown = "skipped (--dry)" if message is None else (picked_tool(message), message.content)
        print(f"{messages[-1]['content']!r}\n  VAKYN: {v and (v['pick'], v['confidence'])}  chat model: {shown}")
    print(f"log: {LOG_PATH}")
