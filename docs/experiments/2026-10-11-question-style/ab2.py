import json, itertools, statistics as st
from ab import ask, PROPS
NAMES = ["Alice", "Bob", "Carol", "Dan"]
ORD = ["first", "second", "third", "fourth"]
V = {"state.path": "state.thread.messages[{i}].text", "backtick": "`thread.messages[{i}].text`",
     "plain name": "{W}'s message", "plain position": "the {o} message in the thread"}
res = {v: [] for v in V}
for q, pos, neg in PROPS:
    for k in range(4):  # the positive message sits at position k, three negatives elsewhere
        texts = [pos if i == k else neg for i in range(4)]
        state = {"thread": {"messages": [{"from": NAMES[i], "text": t} for i, t in enumerate(texts)]}}
        qs, truth = {}, {}
        for v, tmpl in V.items():
            for i in range(4):
                qid = f"{v.replace(' ', '_').replace('.', '_')}_{i}"
                qs[qid] = {"type": "noul", "instructions": q.format(X=tmpl.format(i=i, W=NAMES[i], o=ORD[i]))}
                truth[qid] = (v, i == k)
        ans = ask(state, qs)
        for qid, (v, label) in truth.items():
            p = ans[qid]["noul"]
            res[v].append(((p >= 0.5) == label, p if label else 1 - p))
print("TEST 1b: 4 similar messages, refer to one (128 questions per row)")
for v, xs in res.items():
    print(f"{v:15} {sum(x[0] for x in xs):>3}/{len(xs):<4} mean p(right) {st.mean(x[1] for x in xs):.3f}  min {min(x[1] for x in xs):.2f}")
