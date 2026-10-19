# Wording tuned: intent (choice) on vakyn-fast

Start: `intent.v1.request.json` (53dc5b11bd9c). Best: `intent.v2.request.json` (4c7ff97b8e62). Verdict: **promote**.

| Metric | Dev, start | Dev, best | Reserved, start | Reserved, best |
|---|---|---|---|---|
| accuracy | 0.477 | 0.955 | 0.650 | 0.850 |
| right / cases | 21 / 44 | 42 / 44 | 13 / 20 | 17 / 20 |

## Rules added (each with the misses it was written for)

- DSP -> TRF, DSP -> FEE, CRD -> OTH, CRD -> ACC: bare codes; describe what belongs in every option

## Rounds

1. `intent.v2.request.json`: dev 0.955, kept

Model calls used: 128 (estimate was 128).
