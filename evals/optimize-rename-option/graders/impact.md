---
type: llm
---

Judge only this one point; ignore everything else in the answer.

PASS if the answer explains that renaming the option keys breaks or changes the code that reads them
(the `answer.choice == "DSP"` branch in app/route.py, and the logged answers or report, which would
no longer compare with the old codes). FAIL if it does not mention the impact on their code or
stored answers.
