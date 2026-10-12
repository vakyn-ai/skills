// BEFORE: Vercel AI SDK `experimental_decide` through AI Gateway (AI_GATEWAY_API_KEY).
// A plain model string routes through AI Gateway.
import { experimental_decide as decide } from "ai";

export async function triage(message: string) {
  const result = await decide({
    model: "typesafe-ai/jev",
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
  return { team: result.answers.team.choice, refund: result.answers.refund.probability };
}
