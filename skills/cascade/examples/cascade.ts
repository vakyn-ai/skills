// Cheap draft, VAKYN check, expensive model only when the draft fails. Side by side first.
//
// npm install @typesafe-ai/sdk openai
// Needs TYPESAFE_BASE_URL and TYPESAFE_API_KEY (https://api.vakyn.com or your own server, and a vk_ key). Outside --demo, also
// CHEAP_MODEL and EXPENSIVE_MODEL, plus your chat-model key (OPENAI_API_KEY, or CHEAP_API_KEY /
// EXPENSIVE_API_KEY with CHEAP_BASE_URL / EXPENSIVE_BASE_URL for any OpenAI-compatible endpoint).
//
// Settings (environment), the same as cascade.py:
//   CASCADE_MODE            side_by_side (default) | cascade
//   CASCADE_MIN_CONFIDENCE  accept a draft only as `supported` at or above this (default 0.8)
//   CASCADE_PER_CLAIM_FROM  drafts with this many sentences or more are also checked per sentence (default 4)
//   CASCADE_LOG, CASCADE_REVIEW  JSON lines log and review queue
//
// `npx tsx cascade.ts --demo` runs sample questions with canned drafts: no chat-model key needed.
import OpenAI from "openai";
import { choice, TypeSafeClient } from "@typesafe-ai/sdk";
import { appendFileSync } from "node:fs";

const MODE = process.env.CASCADE_MODE ?? "side_by_side";
const MIN_CONFIDENCE = Number(process.env.CASCADE_MIN_CONFIDENCE ?? "0.8"); // starting value; set yours with check
const PER_CLAIM_FROM = Number(process.env.CASCADE_PER_CLAIM_FROM ?? "4");
const LOG_PATH = process.env.CASCADE_LOG ?? "cascade-log.jsonl";
const REVIEW_PATH = process.env.CASCADE_REVIEW ?? "cascade-review.jsonl";
const DEMO = process.argv.includes("--demo");
const CHEAP_MODEL = DEMO ? "demo-cheap" : process.env.CHEAP_MODEL!;
const EXPENSIVE_MODEL = DEMO ? "demo-expensive" : process.env.EXPENSIVE_MODEL!;
const SOURCE_BUDGET_TOKENS = 24_000; // sources share the 32,768-token state with the question, draft and claims

const DRAFT_PROMPT =
  "Answer the customer's question using only the help articles below. If they do not contain " +
  "the answer, say you could not find it and that a person will follow up. Do not add facts.";
const DECLINE = "I could not find this in our help articles. A member of our team will reply to you.";
const HOLD = "Thanks, a member of our team will check this and reply to you.";

const VERDICT = {
  supported: "Every sentence in the draft is stated in the sources, and the draft answers the question",
  unsupported:
    "At least one sentence in the draft states something the sources do not say or say differently: a number, a date, a step, a promise",
  cannot_answer_from_sources: "The sources do not contain the answer to the question, whatever the draft says",
  off_topic: "The draft does not answer the question that was asked",
};
const CLAIM = {
  supported: "The sources state this sentence",
  contradicted: "The sources state something that makes this sentence false",
  not_in_sources: "The sources do not say enough to back or refute this sentence",
};
const MATCH = { // side by side only: the cheap draft against the expensive answer (agreement, not accuracy)
  same_answer: "The draft gives the same answer with the same facts, numbers and steps as the reference; wording may differ",
  draft_incomplete: "The draft gives the same answer but leaves out a fact or step that the reference gives",
  different_answer: "The draft gives a different answer, or a different fact, number or step, than the reference",
  cannot_compare: "The draft or the reference does not answer the question",
};

type Source = { id: string; text: string };
type Usage = { in: number | null; out: number | null } | null;
type Drafter = (question: string, sources: Source[]) => Promise<[string, Usage]>;
type Claim = { text: string; pick: string; confidence: number };
type Verdict = {
  pick: string; confidence: number; probabilities: Record<string, number>;
  requestId: string | undefined; claims: Claim[] | null;
};

const vakyn = new TypeSafeClient({ timeout: 60_000 });

// Keep sources in retrieval order while they fit (about 4 characters per token).
function trimSources(sources: Source[], budget = SOURCE_BUDGET_TOKENS): Source[] {
  const kept: Source[] = [];
  let used = 0;
  for (const s of sources) {
    const size = Math.floor(JSON.stringify(s).length / 4) + 1;
    if (used + size > budget) break;
    kept.push(s);
    used += size;
  }
  return kept;
}

// Sentences, with short ones ("Yes.", "Sure!") joined to the next: alone they state nothing.
function splitClaims(draft: string): string[] {
  const claims: string[] = [];
  let carry = "";
  for (const part of draft.trim().split(/(?<=[.!?])\s+/).filter(Boolean)) {
    const p = `${carry} ${part}`.trim();
    if (p.split(/\s+/).length < 4) carry = p;
    else { claims.push(p); carry = ""; }
  }
  if (carry) claims.push(carry);
  return claims;
}

// VAKYN's verdict on a draft. Long drafts also get one question per sentence, in the same request.
async function check(question: string, sources: Source[], draft: string): Promise<Verdict> {
  const state: { question: string; sources: Source[]; draft: string; claims?: Record<string, string> } =
    { question, sources, draft };
  const questions: Record<string, ReturnType<typeof choice>> = {
    verdict: choice("Is the draft answer in state.draft backed by state.sources, as an answer to state.question?", VERDICT),
  };
  const sentences = PER_CLAIM_FROM > 0 ? splitClaims(draft) : [];
  const claims = sentences.length >= PER_CLAIM_FROM && PER_CLAIM_FROM > 0
    ? Object.fromEntries(sentences.map((c, i) => [`c${i + 1}`, c])) : null;
  if (claims) {
    state.claims = claims;
    for (const key of Object.keys(claims)) {
      questions[key] = choice(`Is the sentence in state.claims.${key} backed by state.sources?`, CLAIM);
    }
  }
  const { data, requestId } = await vakyn.systemOne({ state, questions }).withResponse();
  const v = data.answers.verdict;
  if (!(v.choice in VERDICT)) throw new Error(`unexpected verdict ${v.choice}`); // an offered option only
  return {
    pick: v.choice, confidence: v.confidence, probabilities: v.probabilities, requestId,
    claims: claims && Object.entries(claims).map(([k, text]) => ({
      text, pick: data.answers[k].choice, confidence: data.answers[k].confidence,
    })),
  };
}

// Send a draft only when the verdict and every checked sentence are `supported` above the bar.
const accepted = (v: Verdict) =>
  v.pick === "supported" && v.confidence >= MIN_CONFIDENCE &&
  (v.claims ?? []).every((c) => c.pick === "supported" && c.confidence >= MIN_CONFIDENCE);

async function compare(question: string, draft: string, reference: string): Promise<string> {
  const { answers } = await vakyn.systemOne({
    state: { question, reference_answer: reference, draft },
    questions: {
      match: choice("Compared with the reference answer in state.reference_answer, how does the draft in state.draft answer state.question?", MATCH),
    },
  });
  return answers.match.choice;
}

function makeDrafter(model: string, baseUrlEnv: string, keyEnv: string): Drafter {
  if (DEMO) return async (question, sources) => demoDraft(model, question, sources);
  const client = new OpenAI({
    baseURL: process.env[baseUrlEnv], apiKey: process.env[keyEnv] ?? process.env.OPENAI_API_KEY,
  });
  return async (question, sources) => {
    const r = await client.chat.completions.create({
      model,
      messages: [
        { role: "system", content: DRAFT_PROMPT },
        { role: "user", content: JSON.stringify({ help_articles: sources, question }) },
      ],
    });
    const usage = r.usage ? { in: r.usage.prompt_tokens, out: r.usage.completion_tokens } : null;
    return [r.choices[0].message.content ?? "", usage];
  };
}

async function timed<T>(fn: () => Promise<T>): Promise<[T, number]> {
  const t = performance.now();
  const out = await fn();
  return [out, Math.round(performance.now() - t)];
}

// Returns the text to send. Writes one log line with the shared field names first.
export async function answer(question: string, raw: Source[], cheap: Drafter, expensive: Drafter) {
  const sources = trimSources(raw);
  const ms: Record<string, number> = {};
  const tokens: Record<string, Usage> = { cheap: null, expensive: null };
  const texts: Record<string, string> = { question };
  const expPromise = MODE === "side_by_side" ? timed(() => expensive(question, sources)) : null;

  let draft: string;
  [[draft, tokens.cheap], ms.cheap] = await timed(() => cheap(question, sources));
  texts.cheap_draft = draft;
  let v: Verdict | null = null;
  try {
    [v, ms.check] = await timed(() => check(question, sources, draft));
  } catch (err) { // VAKYN down or a bad answer: behave as today, the expensive model answers
    console.error(`VAKYN unavailable: ${err}`);
  }
  const route = v === null ? "escalate"
    : accepted(v) ? "accept_cheap"
    : v.pick === "cannot_answer_from_sources" && v.confidence >= MIN_CONFIDENCE ? "decline" // same sources, same gap
    : "escalate";

  let used: string, reply: string;
  let chatPick: string | null = null, agree: boolean | null = null;
  let expensiveCheck: { pick: string; confidence: number; request_id?: string } | null = null;
  if (expPromise) { // side by side: customers get the expensive answer, as today
    let expText: string;
    [[expText, tokens.expensive], ms.expensive] = await expPromise;
    texts.expensive_answer = expText;
    try {
      chatPick = await compare(question, draft, expText);
      agree = (route === "accept_cheap") === (chatPick === "same_answer");
    } catch (err) { console.error(`VAKYN compare failed: ${err}`); }
    [used, reply] = ["expensive", expText];
  } else if (route === "accept_cheap") [used, reply] = ["cheap", draft];
  else if (route === "decline") [used, reply] = ["decline", DECLINE];
  else { // escalate once; never loop
    let expText: string;
    [[expText, tokens.expensive], ms.expensive] = await timed(() => expensive(question, sources));
    texts.expensive_answer = expText;
    let ok: boolean;
    try {
      const [v2, t2] = await timed(() => check(question, sources, expText));
      ms.check2 = t2;
      expensiveCheck = { pick: v2.pick, confidence: v2.confidence, request_id: v2.requestId };
      ok = accepted(v2);
    } catch (err) { // VAKYN down: send the expensive answer unchecked, as before the cascade
      console.error(`VAKYN unavailable: ${err}`);
      ok = true;
    }
    if (ok) [used, reply] = ["expensive", expText];
    else { // failed twice: a person decides
      [used, reply] = ["person", HOLD];
      appendFileSync(REVIEW_PATH, JSON.stringify({ question, sources, cheap_draft: draft, expensive_answer: expText, verdicts: [v, expensiveCheck] }) + "\n");
    }
  }
  const line = {
    ts: new Date().toISOString(), request_id: v?.requestId ?? null, question: "draft_check",
    vakyn_pick: v?.pick ?? null, vakyn_confidence: v?.confidence ?? null, vakyn_probabilities: v?.probabilities ?? null,
    chat_pick: chatPick, agree, mode: MODE, used, route, escalated: route === "escalate", claims: v?.claims ?? null,
    expensive_check: expensiveCheck, cheap_model: CHEAP_MODEL, expensive_model: EXPENSIVE_MODEL,
    tokens, ms, label: null, texts,
  };
  appendFileSync(LOG_PATH, JSON.stringify(line) + "\n");
  return { reply, line };
}

// --- demo: canned drafts in place of the chat models ------------------------------------------
const KB: Record<string, string> = {
  "kb-112": "Refunds for annual plans. If you cancel an annual Tallyfox plan within 14 days of the purchase date, we refund the full amount to the card used for the purchase. After 14 days, annual plans are not refunded; the plan stays active until the end of the paid year. Monthly plans are never refunded. To ask for a refund, open Settings > Billing and choose Cancel plan.",
  "kb-140": "Plans and users. Starter includes up to 3 users. Team includes up to 15 users. Business has no user limit.",
  "kb-087": "Changing your plan. You can switch from monthly to annual billing at any time in Settings > Billing. The unused part of the current month is credited to the annual price. Switching from annual to monthly takes effect at the end of the paid year.",
};
const DEMO_CASES: [string, string[], string, string][] = [ // question, source ids, cheap draft, expensive answer
  ["I bought the annual plan last week by mistake. Can I get my money back?", ["kb-112"],
    "Yes. You are within 14 days of buying it, so cancel in Settings > Billing (Cancel plan) and the full amount goes back to your card.",
    "Yes. Annual plans cancelled within 14 days of purchase are refunded in full to the card you paid with. Open Settings > Billing and choose Cancel plan."],
  ["How many people can use our account on the Starter plan?", ["kb-140"],
    "The Starter plan includes up to 5 users.",
    "Starter includes up to 3 users. For more, Team allows up to 15 and Business has no limit."],
  ["Can I pay my subscription by bank transfer instead of card?", ["kb-112", "kb-087"],
    "Yes, you can pay by bank transfer. Choose Bank transfer in Settings > Billing and use the reference shown there.",
    "I could not find payment by bank transfer in our help articles. A member of our team will reply to you."],
  ["We are on monthly billing. How do we switch to annual and what happens to this month?", ["kb-087"],
    "You can switch to annual billing at any time. Open Settings > Billing and choose annual. The unused part of this month is credited to the annual price. You also get 10% off the annual price when you switch.",
    "Open Settings > Billing and switch to annual billing; you can do it at any time. The unused part of the current month is credited to the annual price."],
];

function demoDraft(model: string, question: string, sources: Source[]): [string, Usage] {
  const c = DEMO_CASES.find((x) => x[0] === question)!;
  const text = model === "demo-cheap" ? c[2] : c[3];
  const prompt = DRAFT_PROMPT + JSON.stringify({ help_articles: sources, question });
  return [text, { in: Math.floor(prompt.length / 4), out: Math.floor(text.length / 4) }]; // estimates
}

const cheap = makeDrafter(CHEAP_MODEL, "CHEAP_BASE_URL", "CHEAP_API_KEY");
const expensive = makeDrafter(EXPENSIVE_MODEL, "EXPENSIVE_BASE_URL", "EXPENSIVE_API_KEY");
for (const [question, ids] of DEMO_CASES) { // without --demo, the same questions go to your chat models
  const { line } = await answer(question, ids.map((id) => ({ id, text: KB[id] })), cheap, expensive);
  console.log(`${question}\n  ${line.vakyn_pick} ${line.vakyn_confidence} -> ${line.route}, used ${line.used}` +
    (line.chat_pick ? `, vs expensive: ${line.chat_pick}` : ""));
  for (const c of line.claims ?? []) console.log(`    sentence ${c.pick.padEnd(15)} ${c.confidence.toFixed(2)}  ${c.text}`);
}
console.log(`log: ${LOG_PATH}`);
