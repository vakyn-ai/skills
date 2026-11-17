"""promptfoo assertion: grade each output with VAKYN against the support-reply rubric.

promptfooconfig.yaml:
    defaultTest:
      assert:
        - type: python
          value: file://vakyn_assert.py

promptfoo calls get_assert(output, context) for every test; context["vars"] holds the test's
variables (here customer_message). The return value is a promptfoo grading result: pass, score,
reason, one component result per criterion, and named scores for the promptfoo viewer.
Needs Python 3 only (any Python promptfoo runs), VAKYN_API_KEY (and VAKYN_BASE_URL if not VAKYN Cloud).
"""

from judge import ask
from rubric import CRITERIA, criterion_results, overall


def get_assert(output, context):
    item = {"input": context["vars"]["customer_message"], "output": output}
    answers, request_id = ask(item)
    results = criterion_results(answers, CRITERIA)
    verdict = overall(results)
    components = [
        {"pass": res["verdict"] == "pass", "score": res["value"], "reason": f"{name}: {res['verdict']}"}
        for name, res in results.items()
    ]
    return {
        "pass": verdict["verdict"] == "pass",  # "review" fails the test, so a person looks at it
        "score": verdict["weighted"],
        "reason": f"{verdict['verdict']}; failed {verdict['failed'] or 'none'}; unsure {verdict['unsure'] or 'none'}; "
                  f"request {request_id}",
        "componentResults": components,
        "named_scores": {name: res["value"] for name, res in results.items()},
    }
