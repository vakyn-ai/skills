// AFTER: the same listing review, with the decisions compiled into VAKYN questions.
//
// Before: schema-zod-before.ts, where generateObject fills all of ListingReview.
// After:  VAKYN answers decision, issues (one noul per label), seller.looks_like_business and
//         quality; the chat model writes only suggested_title, plus any field VAKYN was unsure
//         about. Code rebuilds the same ListingReview, so callers do not change.
//
// npm install @typesafe-ai/sdk ai @ai-sdk/openai zod
// Needs TYPESAFE_BASE_URL and TYPESAFE_API_KEY (your VAKYN server and key) and OPENAI_API_KEY.
//
// Settings (environment):
//   VAKYN_SCHEMA_MODE  side_by_side (default): the old generateObject call is used, as before;
//                      VAKYN's answers are logged next to it. vakyn: the rebuilt object is used.
//   VAKYN_SCHEMA_LOG   JSON lines log, one line per question (default vakyn-schema.jsonl).
//
// npx tsx schema_zod_after.ts --stub      runs two sample listings; the chat model is stubbed
// npx tsx schema_zod_after.ts --request   prints the compiled request for the first sample
import { openai } from "@ai-sdk/openai";
import { choice, noul, score, TypeSafeClient } from "@typesafe-ai/sdk";
import { generateObject } from "ai";
import { appendFileSync } from "node:fs";
import { z } from "zod";

const MODE = process.env.VAKYN_SCHEMA_MODE ?? "side_by_side";
const LOG_PATH = process.env.VAKYN_SCHEMA_LOG ?? "vakyn-schema.jsonl";
const MIN_CONFIDENCE = 0.6; // starting value; set yours with check
const YES_AT = 0.8, NO_AT = 0.2; // starting value; set yours with check (between them: unsure)
const STUB = process.argv.includes("--stub");

// ---- The app's schema, unchanged (from schema-zod-before.ts) --------------------------------------
const DECISIONS = ["approve", "needs_edit", "reject"] as const;
const ISSUES = ["prohibited_item", "misleading_price", "contact_details", "missing_condition"] as const;
export const ListingReview = z.object({
  decision: z
    .enum(DECISIONS)
    .describe("approve: can go live as is. needs_edit: allowed, but the seller must fix the text. reject: not allowed on the market."),
  issues: z.array(z.enum(ISSUES)).describe("Every problem in the listing text. Empty when there is none."),
  seller: z.object({
    looks_like_business: z.boolean().describe("True when the text reads like a shop or trader, not a private person."),
  }),
  quality: z.number().int().min(1).max(4).describe("How well the text describes the item: 1 = poor, 4 = excellent."),
  suggested_title: z.string().describe("A clear title of at most 60 characters."),
});
export type ListingReview = z.infer<typeof ListingReview>;
type FieldName = keyof ListingReview;

// ---- The compiled questions -------------------------------------------------------------------------
// Field descriptions became the criteria. Each question's text carries the meaning: question names
// are never sent to VAKYN.
type Issue = (typeof ISSUES)[number];
// list of enums -> one noul per label, each its own yes/no question.
const ISSUE_QUESTIONS: Record<Issue, string> = {
  prohibited_item: "Does state.listing offer an item that is not allowed for sale: weapons, medicines, live animals, or counterfeit goods?",
  misleading_price: "Does the price in state.listing mislead the buyer, such as a price that differs from the one in the text or a hidden extra fee?",
  contact_details: "Does state.listing contain a phone number, email address or social media handle, even spelled out in words?",
  missing_condition: "Does state.listing leave out the condition of the item (new, used, damaged)?",
};
const QUESTIONS = {
  // enum -> choice, one option per value, plus an escape: a forced pick on a text that is not a listing would be wrong.
  decision: choice("What should Swapyard do with state.listing?", {
    approve: "Can go live as is: an allowed item, the condition stated, a clear price, no contact details in the text",
    needs_edit: "The item is allowed, but the text must change first: it has contact details, an unclear price, or no condition",
    reject: "The item is not allowed for sale (weapons, medicines, live animals, counterfeits), or the listing is a scam",
    cannot_tell: "The text is not a listing, or too short to judge",
  }),
  ...(Object.fromEntries(ISSUES.map((i) => [`issue_${i}`, noul(ISSUE_QUESTIONS[i])])) as Record<
    `issue_${Issue}`,
    ReturnType<typeof noul>
  >),
  // nested object -> a flat, named question; code puts it back under seller.
  seller_looks_like_business: noul("Does state.listing read like it was written by a shop or trader?", {
    true: "A shop or trader: stock counts, several sizes, invoices, a company name, delivery terms",
    false: "A private person selling their own item",
  }),
  // int 1-4 -> score, four levels in words; level 0 is quality 1.
  quality: score("How well does state.listing describe the item for a buyer?", [
    "Poor: a few words; the buyer cannot tell what the item is",
    "Basic: says what the item is, but little else",
    "Good: the item, its condition and its size or model",
    "Excellent: everything a buyer asks: item, condition, size or model, flaws, and how to collect or ship",
  ]),
};
const VAKYN_FIELDS: FieldName[] = ["decision", "issues", "seller", "quality"];
const KEPT_FIELDS: FieldName[] = ["suggested_title"]; // free text: stays with the chat model

const vakyn = new TypeSafeClient({ timeout: 30_000 });

// ---- VAKYN answers -> field values -----------------------------------------------------------------
type Answered = {
  values: Partial<ListingReview>; // only the fields VAKYN is sure about
  top: Partial<Record<FieldName, unknown>>; // VAKYN's top answer per field, sure or not, for the log
  confidence: Partial<Record<FieldName, number>>;
  requestId?: string;
};

async function askVakyn(listing: string): Promise<Answered | null> {
  let res;
  try {
    res = await vakyn.systemOne({ state: { listing }, questions: QUESTIONS }).withResponse();
  } catch (err) {
    console.error("VAKYN unavailable:", err); // every field then goes to the chat model
    return null;
  }
  const a = res.data.answers;
  const yesNo = (p: number) => (p >= YES_AT ? true : p <= NO_AT ? false : null);
  const sure = (p: number) => Math.round(Math.abs(2 * p - 1) * 100) / 100;
  const out: Answered = { values: {}, top: {}, confidence: {}, requestId: res.requestId };

  const d = a.decision;
  if ((DECISIONS as readonly string[]).includes(d.choice) && d.confidence >= MIN_CONFIDENCE) {
    out.values.decision = d.choice as ListingReview["decision"]; // `cannot_tell` stays unanswered
  }
  out.top.decision = d.choice;
  out.confidence.decision = d.confidence;

  const issueAnswers = ISSUES.map((i) => [i, yesNo(a[`issue_${i}`].noul)] as const);
  if (issueAnswers.every(([, yes]) => yes !== null)) {  // the list is only known when every label is
    out.values.issues = issueAnswers.filter(([, yes]) => yes).map(([i]) => i);
  }
  out.top.issues = ISSUES.filter((i) => a[`issue_${i}`].noul >= 0.5);
  out.confidence.issues = Math.min(...ISSUES.map((i) => sure(a[`issue_${i}`].noul)));

  const biz = yesNo(a.seller_looks_like_business.noul);
  if (biz !== null) out.values.seller = { looks_like_business: biz };
  out.top.seller = { looks_like_business: a.seller_looks_like_business.noul >= 0.5 };
  out.confidence.seller = sure(a.seller_looks_like_business.noul);

  if (a.quality.confidence >= MIN_CONFIDENCE) out.values.quality = Math.round(a.quality.score) + 1; // 0..3 -> 1..4
  out.top.quality = Math.round(a.quality.score) + 1;
  out.confidence.quality = a.quality.confidence;

  return out;
}

// ---- The chat model: only the fields VAKYN does not answer ------------------------------------------
async function chatFill(listing: string, fields: FieldName[]): Promise<Partial<ListingReview>> {
  const mask = Object.fromEntries(fields.map((f) => [f, true])) as Partial<Record<FieldName, true>>;
  const Part = ListingReview.pick(mask); // same types and descriptions, fewer fields
  if (STUB) {
    // No chat-model key in this demo: fixed values that pass the same validation.
    const stub: ListingReview = { decision: "approve", issues: [], seller: { looks_like_business: false },
      quality: 2, suggested_title: `(stub title) ${listing.slice(0, 40)}` };
    return Part.parse(Object.fromEntries(fields.map((f) => [f, stub[f]])));
  }
  const { object } = await generateObject({
    model: openai("gpt-4.1-mini"),
    schema: Part,
    prompt: `Review this listing for Swapyard, a second-hand marketplace.\n\n${listing}`,
  });
  return object as Partial<ListingReview>;
}

// ---- Rebuild the same typed object ------------------------------------------------------------------
export interface Reviewed {
  value: ListingReview; // the same type callers used before
  confidence: Record<FieldName, number | null>; // VAKYN's confidence; null when the chat model wrote it
  source: Record<FieldName, "vakyn" | "chat">;
  requestId?: string;
}

export async function reviewListing(listing: string): Promise<Reviewed> {
  const all = Object.keys(ListingReview.shape) as FieldName[];
  const v = await askVakyn(listing);
  const fromChat = MODE === "side_by_side" || !v
    ? await chatFill(listing, all) // exactly as before
    : await chatFill(listing, [...KEPT_FIELDS, ...VAKYN_FIELDS.filter((f) => v.values[f] === undefined)]);
  if (v) log(v, fromChat);
  const merged = MODE === "side_by_side" ? fromChat : { ...v?.values, ...fromChat };
  const value = ListingReview.parse(merged); // validated: a wrong value fails here, not downstream
  const byChat = (f: FieldName) => f in fromChat;
  return {
    value,
    confidence: Object.fromEntries(all.map((f) => [f, byChat(f) ? null : v?.confidence[f] ?? null])) as Reviewed["confidence"],
    source: Object.fromEntries(all.map((f) => [f, byChat(f) ? "chat" : "vakyn"])) as Reviewed["source"],
    requestId: v?.requestId,
  };
}

// One JSON line per decision field: VAKYN's value and confidence next to the chat model's.
function log(v: Answered, chat: Partial<ListingReview>) {
  const ts = new Date().toISOString();
  for (const f of VAKYN_FIELDS) {
    const mine = v.top[f] ?? null, theirs = chat[f] ?? null;
    appendFileSync(LOG_PATH, JSON.stringify({ ts, request_id: v.requestId ?? null, question: f, mode: MODE,
      vakyn_pick: mine, vakyn_confidence: v.confidence[f] ?? null, vakyn_sure: v.values[f] !== undefined, chat_pick: theirs,
      agree: mine === null || theirs === null ? null : JSON.stringify(mine) === JSON.stringify(theirs) }) + "\n");
  }
}

const SAMPLES = [
  "Kids bike, 16 inch, blue. Used for two summers, brakes and tyres fine, small scratch on the frame. " +
    "Pick up in Leeds. 45 pounds. Text me on oh seven seven double-oh 900 123 for quick sale.",
  "NEW iPhone cases, all models in stock, 200+ units. Wholesale prices, invoice on request, ships next day.",
];

if (process.argv.includes("--request")) {
  console.log(JSON.stringify({ model: "jev-latest", state: { listing: SAMPLES[0] }, questions: QUESTIONS }, null, 2));
} else if (process.argv[1]?.endsWith("schema_zod_after.ts")) {
  for (const s of SAMPLES) {
    const r = await reviewListing(s);
    console.log(JSON.stringify(r.value));
    console.log("  confidence", JSON.stringify(r.confidence));
    console.log("  source    ", JSON.stringify(r.source));
  }
}
