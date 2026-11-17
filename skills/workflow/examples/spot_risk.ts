// Flag messages that need a person: one noul per risk, combined in code. Built-in fetch only, nothing to install.
// Needs VAKYN_API_KEY. VAKYN_BASE_URL is optional (default https://api.vakyn.com).

// Several risks can be true at once, so each is its own noul (not one choice).
const RISKS = {
  refund_demand: {
    type: "noul",
    instructions: "Does state.message ask for money back?",
    criteria: {
      true: "Asks for a refund, a chargeback or compensation in money",
      false: "Asks for something else, such as a repair, a swap or information",
    },
  },
  legal_threat: {
    type: "noul",
    instructions: "Does state.message threaten legal action?",
    criteria: {
      true: "Mentions a lawyer, court, a claim, or reporting the company to an authority",
      false: "Complains without any legal step",
    },
  },
  safety_issue: {
    type: "noul",
    instructions: "Does state.message describe a danger to the safety of people?",
    criteria: {
      true: "Fire, smoke, burns, electric shock, injury, a child or pet put at risk",
      false: "The problem only affects the product, the order or money",
    },
  },
  public_complaint: {
    type: "noul",
    instructions: "Does state.message threaten to complain in public?",
    criteria: {
      true: "Threatens a bad review, a social media post or going to the press",
      false: "No public complaint is mentioned",
    },
  },
};
const FLAG = 0.8; // at or above: the risk is there. Starting value; set yours with check
const CLEAR = 0.2; // at or below: the risk is not there; in between is unsure. Starting value

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

async function screen(message: string, order: Record<string, string | number>): Promise<[string, string[]]> {
  const answers: Record<string, { noul: number }> = await decide({ channel: "chat", order, message }, RISKS);
  const p = Object.fromEntries(Object.keys(RISKS).map((k) => [k, answers[k].noul]));
  const flagged = Object.keys(p).filter((k) => p[k] >= FLAG);
  const unsure = Object.keys(p).filter((k) => p[k] > CLEAR && p[k] < FLAG);
  if (p.safety_issue > CLEAR) return ["safety_team_now", [...flagged, ...unsure]]; // safety first, even when unsure
  if (flagged.includes("legal_threat")) return ["legal_team", flagged];
  if (flagged.length || unsure.length) return ["person_review", [...flagged, ...unsure]];
  return ["normal_queue", []];
}

const order = { product: "Ember 2000 fan heater", delivered_days_ago: 9 };
for (const msg of [
  "The heater started smoking last night and the plug is melted. I want a full refund.",
  "Third time asking. Refund me by Friday or my lawyer will file a claim, and I will post about it everywhere.",
  "Does the heater have a timer? I could not find it in the manual.",
]) {
  const [queue, why] = await screen(msg, order);
  console.log(queue.padEnd(16), why.join(", ").padEnd(45), "|", msg.slice(0, 50));
}

export {}; // a module, so top-level await works
