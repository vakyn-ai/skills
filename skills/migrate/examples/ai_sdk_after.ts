// AFTER: the same `experimental_decide` call on VAKYN Cloud (or your own open-server), through the
// TypeSafe provider for the AI SDK (npm install ai @ai-sdk/typesafe-ai; `ai` 7.0.128 or later).
//
// This provider uses its OWN variable names, and its base URL INCLUDES /v1:
//   TYPESAFE_AI_BASE_URL=https://api.vakyn.com/v1   (or your own server's URL + /v1)
//   TYPESAFE_AI_API_KEY=vk_...            (never in code)
//   DECISION_MODEL=jev-latest             (this app's own setting; rollback: typesafe-ai/jev via AI Gateway)
//
// Run: npx tsx ai_sdk_after.ts
import { experimental_decide as decide } from "ai";
import { typeSafeAi } from "@ai-sdk/typesafe-ai";

const model = typeSafeAi.decisionModel(process.env.DECISION_MODEL ?? "jev-latest");

export async function triage(message: string) {
  const result = await decide({
    model,
    state: { message },
    questions: {
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
      refund: { type: "boolean", instructions: "Does state.message ask for money back?" },
    },
  });
  // `confidence` is not on the answer here; the provider puts it in providerMetadata.
  const confidence = (result.providerMetadata?.typesafe?.confidence ?? {}) as Record<string, number>;
  return {
    team: result.answers.team.choice,
    teamConfidence: confidence.team,
    refund: result.answers.refund.probability,
  };
}

console.log(await triage("I booked two city bikes for Saturday but need to move it to Sunday."));
