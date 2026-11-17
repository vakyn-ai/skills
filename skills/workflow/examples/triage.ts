// Triage a batch of repair requests by trade and urgency, many at a time. Built-in fetch only, nothing to install.
// Needs VAKYN_API_KEY. VAKYN_BASE_URL is optional (default https://api.vakyn.com).

const TRADES = {
  plumbing: "Leaks, taps, toilets, drains, water pressure",
  electrical: "Lights, sockets, fuses, power cuts in the flat",
  heating: "Radiators, boiler, hot water temperature",
  appliance: "Oven, fridge, washing machine or other supplied appliance",
  pests: "Mice, insects or other pests",
  general: "Doors, windows, locks, floors, walls and other fixes inside the flat",
  other: "None of these, or not a repair: noise complaints, parking, questions about rent",
};
const URGENCY = [
  "Routine: cosmetic or minor, fine at the next planned visit",
  "This week: a nuisance, the flat is still usable",
  "Within 24 hours: daily life is hard, or a vulnerable person is affected",
  "Emergency now: danger to people or the building, such as gas smell, sparks or flooding",
] as const;
// Both questions only need the request text, so they go in ONE request per record.
const QUESTIONS = {
  trade: { type: "choice", instructions: "Which trade is needed for the repair request in state.request?", criteria: TRADES },
  urgency: { type: "score", instructions: "How soon does the repair in state.request need someone on site?", criteria: URGENCY },
};
const MAX_IN_FLIGHT = 8; // VAKYN Cloud: under 60 requests/s per key; own server: below --max-queue
const MIN_CONFIDENCE = 0.6; // starting value; set yours with check

type Rec = { unit: string; text: string };
const BASE_URL = process.env.VAKYN_BASE_URL ?? "https://api.vakyn.com";
const MAX_RETRIES = 4; // retries 429 after the delay VAKYN asks for, and 5xx after a short wait

class RateLimitError extends Error {}

type Answers = {
  trade: { choice: string; confidence: number };
  urgency: { score: number; confidence: number; probabilities: Record<string, number> };
};

async function decide(state: unknown, questions: Record<string, unknown>): Promise<Answers> {
  for (let attempt = 0; ; attempt++) {
    const response = await fetch(`${BASE_URL}/v1/systemone`, {
      method: "POST",
      headers: { Authorization: `Bearer ${process.env.VAKYN_API_KEY}`, "Content-Type": "application/json" },
      body: JSON.stringify({ state, questions }),
      signal: AbortSignal.timeout(30_000),
    });
    if (response.ok) return (await response.json()).answers;
    const retryable = response.status === 429 || response.status >= 500;
    if (!retryable || attempt === MAX_RETRIES) {
      if (response.status === 429) throw new RateLimitError("still 429 after retries");
      throw new Error(`VAKYN ${response.status}: ${await response.text()}`);
    }
    const wait = Number(response.headers.get("retry-after")) || 2 ** attempt;
    await new Promise((resolve) => setTimeout(resolve, wait * 1000));
  }
}

async function triage(rec: Rec) {
  try {
    const { trade, urgency } = await decide({ building: "Elm Court", unit: rec.unit, request: rec.text }, QUESTIONS);
    const unsure = trade.choice === "other" || Math.min(trade.confidence, urgency.confidence) < MIN_CONFIDENCE;
    // A rule in code: any real chance of an emergency goes to on-call.
    const queue = (urgency.probabilities["3"] ?? 0) > 0.2 ? "on_call_now" : unsure ? "dispatcher_review" : trade.choice;
    return { ...rec, urgency: urgency.score, queue };
  } catch (e) {
    if (e instanceof RateLimitError) return { ...rec, urgency: 0, queue: "retry_later" }; // still 429 after retries
    throw e;
  }
}

// Bounded concurrency: MAX_IN_FLIGHT workers take records from one shared list.
async function triageAll(records: Rec[]) {
  const results: Awaited<ReturnType<typeof triage>>[] = [];
  let next = 0;
  const worker = async () => {
    while (next < records.length) results.push(await triage(records[next++]));
  };
  await Promise.all(Array.from({ length: MAX_IN_FLIGHT }, worker));
  return results.sort((a, b) => b.urgency - a.urgency); // most urgent first
}

const records: Rec[] = [
  { unit: "3B", text: "The bedroom radiator has been cold for two days and the flat is at 14 degrees. We have a newborn." },
  { unit: "1A", text: "Water is coming through the ceiling above the bathroom light and the light just went off." },
  { unit: "5C", text: "One kitchen cupboard door is a bit loose." },
  { unit: "2D", text: "Saw two mice behind the fridge this week." },
  { unit: "4A", text: "Can I get a second parking permit for my partner?" },
  { unit: "6B", text: "The oven does not heat up anymore, the hob still works." },
];
for (const r of await triageAll(records)) {
  console.log(r.unit.padEnd(4), r.queue.padEnd(18), r.urgency.toFixed(2), r.text.slice(0, 60));
}

export {}; // a module, so top-level await works
