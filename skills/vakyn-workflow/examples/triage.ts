// Triage a batch of repair requests by trade and urgency, many at a time. npm install @typesafe-ai/sdk
// Needs TYPESAFE_BASE_URL and TYPESAFE_API_KEY.
import { choice, RateLimitError, score, TypeSafeClient } from "@typesafe-ai/sdk";

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
  trade: choice("Which trade is needed for the repair request in state.request?", TRADES),
  urgency: score("How soon does the repair in state.request need someone on site?", URGENCY),
};
const MAX_IN_FLIGHT = 8; // stay below the server's queue (--max-queue)
const MIN_CONFIDENCE = 0.6; // a setting; tune it on your own labeled requests (vakyn-check)

type Rec = { unit: string; text: string };
// Retries 429 after the delay the server asks for.
const client = new TypeSafeClient({ timeout: 30_000, retry: { maxRetries: 4 } });

async function triage(rec: Rec) {
  try {
    const { answers } = await client.systemOne({ state: { building: "Elm Court", unit: rec.unit, request: rec.text }, questions: QUESTIONS });
    const { trade, urgency } = answers;
    const unsure = trade.choice === "other" || Math.min(trade.confidence, urgency.confidence) < MIN_CONFIDENCE;
    // A rule in code: any real chance of an emergency goes to on-call.
    const queue = (urgency.probabilities[3] ?? 0) > 0.2 ? "on_call_now" : unsure ? "dispatcher_review" : trade.choice;
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
