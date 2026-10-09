"""promptfoo assertion: grade each output with VAKYN against the support-reply rubric.

promptfooconfig.yaml:
    defaultTest:
      assert:
        - type: python
          value: file://vakyn_assert.py

promptfoo calls get_assert(output, context) for every test; context["vars"] holds the test's
variables (here customer_message). The return value is a promptfoo grading result: pass, score,
reason, one component result per criterion, and named scores for the promptfoo viewer.
Needs typesafe-sdk in the Python promptfoo runs (PROMPTFOO_PYTHON), TYPESAFE_BASE_URL and TYPESAFE_API_KEY.
"""

from typesafe_sdk import TypeSafeClient

from judge import sdk_questions
from rubric import CRITERIA, answers_from_response, build_state, criterion_results, overall

client = TypeSafeClient(timeout=60.0)


def get_assert(output, context):
    item = {"input": context["vars"]["customer_message"], "output": output}
    r = client.system_one(state=build_state(item), questions=sdk_questions())
    results = criterion_results(answers_from_response(r), CRITERIA)
    verdict = overall(results)
    components = [
        {"pass": res["verdict"] == "pass", "score": res["value"], "reason": f"{name}: {res['verdict']}"}
        for name, res in results.items()
    ]
    return {
        "pass": verdict["verdict"] == "pass",  # "review" fails the test, so a person looks at it
        "score": verdict["weighted"],
        "reason": f"{verdict['verdict']}; failed {verdict['failed'] or 'none'}; unsure {verdict['unsure'] or 'none'}; "
                  f"request {r.request_id}",
        "componentResults": components,
        "named_scores": {name: res["value"] for name, res in results.items()},
    }
