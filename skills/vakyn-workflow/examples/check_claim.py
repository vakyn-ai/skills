"""Check each marketing claim against the product spec. pip install typesafe-sdk

Needs TYPESAFE_BASE_URL and TYPESAFE_API_KEY.
"""

from concurrent.futures import ThreadPoolExecutor

from typesafe_sdk import Choice, TypeSafeClient

VERDICTS = {
    "supported": "The spec states facts that make the claim true",
    "contradicted": "The spec states facts that make the claim false",
    "not_enough_evidence": "The spec does not say enough to decide either way",
}
MIN_CONFIDENCE = 0.8  # a published claim needs a high bar; tune it on claims you checked by hand

SPEC = (
    "Wavelet Go portable speaker. Battery: 14 hours at 50% volume. Charging: USB-C, 3.5 hours from "
    "empty with an 18 W charger. Water and dust: IP67, survives 30 minutes at 1 m depth. Weight: 540 g. "
    "Bluetooth 5.3, range up to 30 m. Two speakers can be paired for stereo."
)
COPY = [  # one claim per item: split the copy into sentences in code before asking
    "Wavelet Go charges fully in under two hours.",
    "Drop it in the pool: it survives half an hour underwater.",
    "Pair two speakers for stereo sound.",
    "Made from 80% recycled plastic.",
]

client = TypeSafeClient(timeout=30.0)


def check(claim: str) -> tuple[str, float]:
    r = client.system_one(
        state={"product_spec": SPEC, "claim": claim},
        questions={"verdict": Choice(
            instructions="Does state.product_spec back up the marketing claim in state.claim?",
            criteria=VERDICTS,
        )},
    )
    v = r.choices["verdict"]
    if v.choice != "supported" or v.confidence < MIN_CONFIDENCE:
        return "editor_review", v  # contradicted, unknown or unsure: a person decides before it ships
    return "ok_to_publish", v


with ThreadPoolExecutor(max_workers=4) as pool:  # claims are independent: send them concurrently
    for claim, (action, v) in zip(COPY, pool.map(check, COPY)):
        print(f"{action:14} {v.choice:20} {v.confidence:.2f}  {claim}")
