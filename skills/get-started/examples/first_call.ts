// First call over plain HTTP with the built-in fetch (Node 18+, Bun, Deno); nothing to install.
// Needs VAKYN_API_KEY (vk_...). VAKYN_BASE_URL is optional: https://api.vakyn.com, or your own server.
export {}; // a module, so top-level await works
const BASE_URL = process.env.VAKYN_BASE_URL ?? "https://api.vakyn.com";

const response = await fetch(`${BASE_URL}/v1/systemone`, {
  method: "POST",
  headers: { Authorization: `Bearer ${process.env.VAKYN_API_KEY}`, "Content-Type": "application/json" },
  body: JSON.stringify({
    state: {
      channel: "email",
      customer: { plan: "team", seats: 12 },
      message: "Since this morning nobody on our team can sign in. We have a client demo at 3pm.",
    },
    questions: {
      outage: {
        type: "noul",
        instructions: "Does the customer's message say they cannot use the product right now?",
      },
      team: {
        type: "choice",
        instructions: "Which team should handle the customer's message?",
        criteria: {
          billing: "Invoices, charges and refunds",
          access: "Sign-in, passwords and permissions",
          product: "Bugs and how-to questions",
          other: "None of these teams fits",
        },
      },
      urgency: {
        type: "score",
        instructions: "How soon does the customer's message need a reply?",
        criteria: ["Can wait a few days", "Today", "Within the hour"],
      },
    },
  }),
});
if (!response.ok) throw new Error(`VAKYN ${response.status}: ${await response.text()}`);
const { answers } = await response.json();

console.log("outage :", answers.outage.noul);
console.log("team   :", answers.team.choice, answers.team.confidence);
console.log("urgency:", answers.urgency.score);
console.log("request:", response.headers.get("x-vakyn-request-id"));
