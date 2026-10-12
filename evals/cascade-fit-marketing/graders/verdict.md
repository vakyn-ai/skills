---
type: llm
---

PASS if all hold:
1. It says a cascade does not fit this job as asked (or fits only a narrow part): catchy copy and
   captions are free-form writing with no sources to check a draft against, so "supported by the
   sources" says nothing about whether the copy is good.
2. It does not write a cascade that sends the copy through a supported / unsupported check as if
   it were grounded answers.
3. It offers a sensible alternative or a narrow part that does fit, for example: just use the
   small model and have a person or a rubric grade a sample (offline grading, `judge`), or
   check only the factual product claims (dimensions, materials) against the product data sheet.
FAIL if it recommends the cascade for the creative copy itself, or invents prices or savings.
