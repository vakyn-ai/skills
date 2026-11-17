// AFTER: the same triage on VAKYN Cloud (or your own open-server), as a direct `fetch` call.
// Nothing to install: the AI SDK's `experimental_decide` and the gateway model string are gone.
//
//   VAKYN_API_KEY=vk_...                  (never in code)
//   VAKYN_BASE_URL=https://api.vakyn.com  (optional; root, no /v1; or your own server's URL)
//   VAKYN_MODEL=                          (optional; own open-server: the name from /v1/models)
//
// Two changes in the body: the yes/no question's type "boolean" is "noul", and there is no gateway
// model. In the answers, the yes/no probability is `noul`, and `confidence` sits on the choice
// answer itself. Rollback: keep the old call (ai_sdk_before.ts) behind one setting until the move is done.
//
// Run: npx tsx ai_sdk_after.ts
const BASE_URL = process.env.VAKYN_BASE_URL ?? "https://api.vakyn.com";
const MODEL = process.env.VAKYN_MODEL; // left out on VAKYN Cloud: vakyn-max answers

type Answers = {
  team: { choice: string; confidence: number; probabilities: Record<string, number> };
  refund: { noul: number };
};

// POST /v1/systemone; returns the answers by question name.
async function decide(state: unknown, questions: Record<string, unknown>): Promise<Answers> {
  const response = await fetch(`${BASE_URL}/v1/systemone`, {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.VAKYN_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ state, questions, ...(MODEL ? { model: MODEL } : {}) }),
    signal: AbortSignal.timeout(30_000),
  });
  if (!response.ok) throw new Error(`VAKYN ${response.status}: ${await response.text()}`);
  return (await response.json()).answers;
}

export async function triage(message: string) {
  const answers = await decide(
    { message },
    {
      team: {
        type: "choice",
        instructions: "Which desk should answer state.message?",
        criteria: {
          repairs: "Broken parts, flat tires, brakes, gears",
          bookings: "Reserving, changing or cancelling a rental",
          billing: "Charges, deposits, refunds",
          other: "None of these fits",
        },
      },
      refund: { type: "noul", instructions: "Does state.message ask for money back?" },
    },
  );
  return {
    team: answers.team.choice,
    teamConfidence: answers.team.confidence,
    refund: answers.refund.noul,
  };
}

console.log(await triage("I booked two city bikes for Saturday but need to move it to Sunday."));
