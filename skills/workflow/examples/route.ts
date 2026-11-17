// Route each support ticket to a team. Built-in fetch only, nothing to install.
// Needs VAKYN_API_KEY (vk_...). VAKYN_BASE_URL is optional (default https://api.vakyn.com, or your own server).

const TEAMS = {
  billing: "Invoices, charges, refunds, plan changes and seat counts",
  access: "Signing in, passwords, two-factor codes, user roles and permissions",
  integrations: "Connections to other tools: Slack, webhooks, API tokens, imports and exports",
  bugs: "Something in the app itself is broken, slow or shows an error",
  other: "Not a support request for these teams: sales, partnerships, press, job applications, spam",
};
const MIN_CONFIDENCE = 0.6; // starting value; set yours with check

type Ticket = { channel: string; plan: string; seats: number; subject: string; body: string };

const BASE_URL = process.env.VAKYN_BASE_URL ?? "https://api.vakyn.com";

async function decide(state: unknown, questions: Record<string, unknown>) {
  const response = await fetch(`${BASE_URL}/v1/systemone`, {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.VAKYN_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ state, questions }),
    signal: AbortSignal.timeout(30_000),
  });
  if (!response.ok) throw new Error(`VAKYN ${response.status}: ${await response.text()}`);
  return (await response.json()).answers;
}

// Evidence only: the ticket text and facts from your records. No guesses about the team.
const buildState = (t: Ticket) => ({
  channel: t.channel,
  customer: { plan: t.plan, seats: t.seats },
  subject: t.subject,
  message: t.body,
});

async function route(t: Ticket): Promise<[string, number]> {
  const answers = await decide(buildState(t), {
    team: {
      type: "choice",
      instructions: "Which support team should handle the ticket in state.subject and state.message?",
      criteria: TEAMS,
    },
  });
  const { choice: team, confidence }: { choice: string; confidence: number } = answers.team;
  if (!(team in TEAMS)) throw new Error(`unexpected option ${team}`); // code checks the pick is one we offered
  if (team === "other" || confidence < MIN_CONFIDENCE) return ["triage_queue", confidence]; // a person routes it
  return [team, confidence];
}

const tickets: Ticket[] = [
  { channel: "web form", plan: "business", seats: 40, subject: "Slack alerts stopped",
    body: "Since we rotated our API token yesterday, the Slack alerts from your app stopped arriving." },
  { channel: "email", plan: "starter", seats: 3, subject: "Charged twice",
    body: "My card shows two charges for March. Please refund one of them." },
  { channel: "email", plan: "none", seats: 0, subject: "Partnership idea",
    body: "We run a podcast for operations teams and would love to talk about a sponsorship." },
];
for (const t of tickets) {
  const [queue, confidence] = await route(t);
  console.log(queue.padEnd(13), confidence.toFixed(2), t.subject);
}

export {}; // a module, so top-level await works
