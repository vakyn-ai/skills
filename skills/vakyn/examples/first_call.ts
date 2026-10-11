// First call with the official SDK: npm install @typesafe-ai/sdk
// Needs TYPESAFE_BASE_URL (your server, e.g. http://127.0.0.1:8080) and TYPESAFE_API_KEY (vk_...).
import { choice, noul, score, TypeSafeClient } from "@typesafe-ai/sdk";

const client = new TypeSafeClient({ timeout: 30_000 });
const { answers } = await client.systemOne({
  state: {
    channel: "email",
    customer: { plan: "team", seats: 12 },
    message: "Since this morning nobody on our team can sign in. We have a client demo at 3pm.",
  },
  questions: {
    outage: noul("Does the customer's message say they cannot use the product right now?"),
    team: choice("Which team should handle the customer's message?", {
      billing: "Invoices, charges and refunds",
      access: "Sign-in, passwords and permissions",
      product: "Bugs and how-to questions",
      other: "None of these teams fits",
    }),
    urgency: score("How soon does the customer's message need a reply?", [
      "Can wait a few days",
      "Today",
      "Within the hour",
    ]),
  },
});

console.log("outage :", answers.outage.noul);
console.log("team   :", answers.team.choice, answers.team.confidence);
console.log("urgency:", answers.urgency.score);
