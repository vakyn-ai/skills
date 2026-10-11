import statistics as st
from ab import ask, PLAIN, STRUCT, LONG
HARD = [
    ("Can I switch to yearly billing and get the discount you advertise?", "sales"),
    ("You charged me the Business price but we are on Team.", "billing"),
    ("Please delete my old user so I can't log in anymore.", "access"),
    ("Remove everything you know about me from your systems.", "privacy"),
    ("I want to cancel and get my unused month back.", "billing"),
    ("What does the Enterprise plan cost if we pay upfront?", "sales"),
    ("My new hire can't see the shared projects.", "access"),
    ("Where are your servers located for GDPR purposes?", "privacy"),
    ("The card on file expired, how do I update it?", "billing"),
    ("Do you have a cheaper plan for students?", "sales"),
    ("Give our auditor read-only access for a week.", "access"),
    ("Which third parties process our customer data?", "privacy"),
    ("We were billed for 3 extra seats we never added.", "billing"),
    ("Is SAML included or is that an add-on?", "sales"),
    ("I keep getting logged out every few minutes.", "access"),
    ("Export all my personal records as a file please.", "privacy"),
    ("Charts don't load in Safari.", "other"),
    ("How do I change the language of the interface?", "other"),
    ("Your price page and my invoice show different amounts.", "billing"),
    ("Transfer ownership of the workspace to my manager.", "access"),
]
res = {"plain": [], "long string": [], "structured": []}
for text, label in HARD:
    qs = {n: {"type": "choice", "instructions": "Which team should handle `message`?", "criteria": c}
          for n, c in (("plain", PLAIN), ("long", LONG), ("structured", STRUCT))}
    a = ask({"message": text}, qs)
    for n, key in (("plain", "plain"), ("long", "long string"), ("structured", "structured")):
        res[key].append((a[n]["choice"] == label, a[n]["probabilities"][label], a[n]["choice"], text))
print("TEST 2b: harder boundaries (20 messages)")
for k, xs in res.items():
    print(f"{k:12} {sum(x[0] for x in xs):>3}/{len(xs):<4} mean p(right) {st.mean(x[1] for x in xs):.3f}")
    print("   wrong:", [f"{x[3][:40]}→{x[2]}" for x in xs if not x[0]])
