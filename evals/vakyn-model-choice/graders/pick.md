---
type: llm
---

PASS if the answer recommends the 4B model (Q8_0, the default) with a lowered context size (for
example --ctx-size 8192 or less, which needs about 8.7 GB), or explains that 4B at full context needs
about 19.7 GB and so the context must be lowered. It gives a start command with
`vakyn serve --model` pointing at a downloaded VAKYN-4B-UQFF folder. FAIL if it recommends a GGUF
file, invents file names or sizes, or picks 0.8B without reason.
