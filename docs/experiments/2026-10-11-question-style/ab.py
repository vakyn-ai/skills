"""A/B tests on the live VAKYN server.

Test 1: how a question refers to a state field (state.x vs `x` vs plain words vs bare key).
Test 2: plain vs structured vs long-string option descriptions in a choice.
Sequential requests (concurrency 1) so load does not move the numbers.
"""
import json, os, urllib.request, statistics as st

BASE = os.environ.get("VAKYN_BASE_URL", "http://127.0.0.1:8080")
KEY = os.environ["VAKYN_API_KEY"]

def ask(state, questions):
    req = urllib.request.Request(f"{BASE}/v1/systemone",
        data=json.dumps({"model": "jev-latest", "state": state, "questions": questions}).encode(),
        headers={"content-type": "application/json", "authorization": f"Bearer {KEY}"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())["answers"]

PROPS = [  # (question template with {X}, positive text, negative text)
    ("Does {X} ask for money back?", "I was charged twice, please give me my money back.",
     "I was charged twice, but I see it has already been fixed, thanks."),
    ("Does {X} set a deadline?", "We need the signed contract by Friday at noon.",
     "Send the signed contract whenever it is convenient."),
    ("Is the writer of {X} angry?", "This is the third time your app lost my data. I am furious.",
     "Your app lost my data once, but support restored it quickly."),
    ("Does {X} ask to close the account?", "Please close my account at the end of this month.",
     "I am thinking about adding two more seats to my account."),
    ("Does {X} threaten legal action?", "If this is not fixed, my lawyer will be in touch.",
     "If this is not fixed, I will call your support line again."),
    ("Does {X} propose a meeting time?", "Can we meet on Tuesday at 3pm to go over the plan?",
     "I have read the plan and have no further comments."),
    ("Does {X} report a bug?", "The export button crashes the app every time I press it.",
     "The export button works, but I would like more file formats."),
    ("Does {X} praise the team?", "Your team was wonderful and solved everything in minutes.",
     "Your team took a week to answer a simple question."),
]

FLAT = {"state.path": "state.message_from_{w}", "backtick": "`message_from_{w}`",
        "plain": "{W}'s message", "bare": "message_from_{w}"}
NESTED = {"state.path": "state.thread.messages[{i}].text", "backtick": "`thread.messages[{i}].text`",
          "plain": "{W}'s message"}

def test1():
    res = {("flat", v): [] for v in FLAT} | {("nested", v): [] for v in NESTED}
    for q, pos, neg in PROPS:
        for a_text, b_text in ((pos, neg), (neg, pos)):
            flat = {"message_from_alice": a_text, "message_from_bob": b_text}
            nested = {"thread": {"messages": [{"from": "Alice", "text": a_text}, {"from": "Bob", "text": b_text}]}}
            for shape, state, variants in (("flat", flat, FLAT), ("nested", nested, NESTED)):
                qs, truth = {}, {}
                for v, tmpl in variants.items():
                    for i, (w, W, text) in enumerate((("alice", "Alice", a_text), ("bob", "Bob", b_text))):
                        qid = f"{v.replace('.', '_')}_{w}"
                        qs[qid] = {"type": "noul", "instructions": q.format(X=tmpl.format(w=w, W=W, i=i))}
                        truth[qid] = (v, text == pos)
                ans = ask(state, qs)
                for qid, (v, label) in truth.items():
                    p = ans[qid]["noul"]
                    res[(shape, v)].append((p >= 0.5) == label and 1 or 0)
                    res[(shape, v)].append(("p", p if label else 1 - p))
    print("TEST 1: field reference style (noul; 32 questions per row)")
    print(f"{'shape':7} {'variant':11} {'correct':>8} {'mean p(right)':>14} {'min p(right)':>13}")
    for (shape, v), xs in res.items():
        acc = [x for x in xs if not isinstance(x, tuple)]
        pr = [x[1] for x in xs if isinstance(x, tuple)]
        print(f"{shape:7} {v:11} {sum(acc):>3}/{len(acc):<4} {st.mean(pr):>14.3f} {min(pr):>13.2f}")

ITEMS = [
    ("How much is the Team plan for 20 users?", "sales"),
    ("I want to delete my account and all my data.", "privacy"),
    ("I can't log in after resetting my password.", "access"),
    ("You charged me again after I cancelled.", "billing"),
    ("Can I get an invoice with our VAT number on it?", "billing"),
    ("Do you offer a discount for nonprofits?", "sales"),
    ("Send me a copy of all the data you hold on me.", "privacy"),
    ("My 2FA codes stopped working.", "access"),
    ("Please remove my colleague's access, she left the company.", "access"),
    ("Which of your plans include single sign-on?", "sales"),
    ("Why was my card declined when the plan renewed?", "billing"),
    ("Do you store our data in the EU?", "privacy"),
    ("I'm locked out after too many attempts.", "access"),
    ("I'd like a refund for the months I didn't use.", "billing"),
    ("Is there a free trial of the Business plan?", "sales"),
    ("Who is your data protection officer?", "privacy"),
    ("The dashboard is very slow today.", "other"),
    ("Can you add a dark mode?", "other"),
    ("Can you tell me what personal data you share with partners?", "privacy"),
    ("Our invoice lists 12 seats but we only have 10.", "billing"),
]
PLAIN = {"billing": "Charges, invoices and refunds", "sales": "Prices and plans",
         "access": "Sign-in and permissions", "privacy": "Personal data requests", "other": "Anything else"}
STRUCT = {
    "billing": {"handles": "money already charged or owed", "includes": ["charges", "invoices", "refunds", "failed payments"],
                "not": "prices of plans before buying (sales)"},
    "sales": {"handles": "buying decisions", "includes": ["prices", "plans and what they include", "discounts", "trials"],
              "not": "charges already made (billing)"},
    "access": {"handles": "getting into the product and who may", "includes": ["sign-in", "passwords", "2FA", "adding or removing users"],
               "not": "deleting an account and its data (privacy)"},
    "privacy": {"handles": "personal data", "includes": ["data export", "account and data deletion", "where data is stored", "data sharing", "data protection officer"],
                "not": "removing a user's access (access)"},
    "other": {"handles": "anything none of the teams above handle", "includes": ["bugs", "speed", "feature requests"]},
}
LONG = {k: f"Handles {v['handles']}: {', '.join(v['includes'])}." + (f" Not {v['not']}." if "not" in v else "")
        for k, v in STRUCT.items()}

def test2():
    res = {"plain": [], "long string": [], "structured": []}
    for text, label in ITEMS:
        qs = {n: {"type": "choice", "instructions": "Which team should handle `message`?", "criteria": c}
              for n, c in (("plain", PLAIN), ("long", LONG), ("structured", STRUCT))}
        ans = ask({"message": text}, qs)
        for n, key in (("plain", "plain"), ("long", "long string"), ("structured", "structured")):
            a = ans[n]
            res[key].append((a["choice"] == label, a["probabilities"][label], a["choice"], text))
    print("\nTEST 2: option descriptions (choice, 20 tricky messages, 5 teams)")
    print(f"{'variant':12} {'correct':>8} {'mean p(right)':>14}")
    for k, xs in res.items():
        print(f"{k:12} {sum(x[0] for x in xs):>3}/{len(xs):<4} {st.mean(x[1] for x in xs):>14.3f}")
    for k, xs in res.items():
        wrong = [f"{x[3][:45]!r}→{x[2]}" for x in xs if not x[0]]
        print(f"  wrong ({k}): {wrong}")


if __name__ == "__main__":
    test1()
    test2()
