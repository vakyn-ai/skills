// Tool pick with VAKYN in an Anthropic SDK app: pick-then-fill, side by side first.
//
// npm install @typesafe-ai/sdk @anthropic-ai/sdk
// Needs TYPESAFE_BASE_URL and TYPESAFE_API_KEY (your VAKYN server and key) and ANTHROPIC_API_KEY.
//
// Settings (environment):
//   VAKYN_TOOL_MODE            side_by_side (default): the chat model still picks and acts; both picks
//                              are logged. vakyn: VAKYN picks, the chat model only fills arguments.
//   VAKYN_TOOL_MIN_CONFIDENCE  in vakyn mode, picks below this go to the chat model (default 0.8).
//   VAKYN_TOOL_LOG             JSON lines log of every pick (default vakyn-tool-picks.jsonl).
//
// `npx tsx tool_pick_anthropic.ts --dry` shows VAKYN's picks without a chat-model key.
import Anthropic from "@anthropic-ai/sdk";
import { choice, TypeSafeClient } from "@typesafe-ai/sdk";
import { appendFileSync, readFileSync } from "node:fs";

const MODE = process.env.VAKYN_TOOL_MODE ?? "side_by_side";
const MIN_CONFIDENCE = Number(process.env.VAKYN_TOOL_MIN_CONFIDENCE ?? "0.8"); // starting value; set yours with check
const LOG_PATH = process.env.VAKYN_TOOL_LOG ?? "vakyn-tool-picks.jsonl";
const CHAT_MODEL = process.env.CHAT_MODEL ?? "claude-haiku-4-5";
const DRY = process.argv.includes("--dry");

// Your app's existing tool list, unchanged. Here: the sample list next to this file.
const TOOLS: Anthropic.Tool[] = JSON.parse(
  readFileSync(new URL("./it-helpdesk-tools.anthropic.json", import.meta.url), "utf8"),
);

// One option per tool: name -> one line from the tool's description. Parameter schemas stay out.
const OPTIONS = {
  lookup_device: "Look up an employee's laptop or phone record: model, OS, warranty, owner",
  reset_mfa: "Clear the employee's two-factor devices so they can enroll a new or replaced phone",
  request_software: "Ask for a software license or install, sent to the manager for approval",
  check_vpn_status: "Check whether the VPN is up and whether the employee's last VPN sign-in failed",
  open_incident: "Open an incident for an outage that affects many people, not one person",
  book_device_swap: "Book an IT desk slot to swap a broken laptop or phone for a loaner",
  none: "No tool is needed now: answer the employee directly",
  ask_user: 'The request does not say what the employee needs ("can you help"); ask them first',
} as const;
type Pick = keyof typeof OPTIONS;
const INSTRUCTIONS = "Which tool should the helpdesk assistant call next to handle state.user_request? " +
  "Use state.last_tool_result: a tool already called does not need to be called again.";

const vakyn = new TypeSafeClient({ timeout: 30_000 });
const chat = DRY ? null : new Anthropic();

interface VakynPick {
  pick: Pick;
  confidence: number;
  probabilities: Record<string, number>;
  requestId: string | undefined;
}

const text = (content: Anthropic.MessageParam["content"]): string =>
  typeof content === "string" ? content : content.map((b) => (b.type === "text" ? b.text : "")).join("");

// Goal, recent turns and the last tool result. User text stays data under its own keys.
function buildState(messages: Anthropic.MessageParam[]) {
  const blocks = messages.flatMap((m) => (typeof m.content === "string" ? [] : m.content));
  const called = blocks.flatMap((b) => (b.type === "tool_use" ? [b.name] : []));
  const results = blocks.flatMap((b) => (b.type === "tool_result" ? [b] : []));
  const last = results.at(-1);
  const turns = messages.filter((m) => text(m.content).trim() !== "").slice(-6);
  const users = turns.filter((m) => m.role === "user");
  return {
    assistant: "IT helpdesk assistant for employees. It calls one tool at a time.",
    user_request: users.length ? text(users[users.length - 1].content) : "",
    recent_turns: turns.map((m) => ({ role: m.role, text: text(m.content).slice(0, 2000) })),
    tools_already_called: called,
    last_tool_result: last ? JSON.stringify(last.content ?? "").slice(0, 8000) : "none yet",
  };
}

// VAKYN's pick, or null when the server cannot answer (the chat model then picks).
async function vakynPick(messages: Anthropic.MessageParam[]): Promise<VakynPick | null> {
  try {
    const { data, requestId } = await vakyn
      .systemOne({ state: buildState(messages), questions: { next_tool: choice(INSTRUCTIONS, OPTIONS) } })
      .withResponse();
    const a = data.answers.next_tool;
    if (!(a.choice in OPTIONS)) return null; // code checks the pick is an offered option
    return { pick: a.choice, confidence: a.confidence, probabilities: { ...a.probabilities }, requestId };
  } catch (err) {
    console.error("VAKYN unavailable:", err); // never block the app on VAKYN
    return null;
  }
}

// One chat-model call. No tools means a plain text reply.
async function chatCall(
  messages: Anthropic.MessageParam[],
  opts: { tools?: Anthropic.Tool[]; toolChoice?: Anthropic.ToolChoice; system?: string } = {},
): Promise<Anthropic.Message | null> {
  if (!chat) return null;
  return chat.messages.create({
    model: CHAT_MODEL,
    max_tokens: 1024,
    messages,
    ...(opts.system ? { system: opts.system } : {}),
    ...(opts.tools ? { tools: opts.tools, tool_choice: opts.toolChoice ?? { type: "auto" } } : {}),
  });
}

function pickedTool(message: Anthropic.Message | null): string | null {
  if (!message) return null;
  const use = message.content.find((b) => b.type === "tool_use");
  return use && use.type === "tool_use" ? use.name : "none";
}

function log(entry: Record<string, unknown>) {
  appendFileSync(LOG_PATH, JSON.stringify({ ts: new Date().toISOString(), ...entry }) + "\n");
}

// Returns the assistant message to act on: a tool call or a text reply.
export async function nextStep(messages: Anthropic.MessageParam[]) {
  let v: VakynPick | null;
  let message: Anthropic.Message | null;
  let used: "chat" | "vakyn";
  if (MODE === "side_by_side") {
    // Both pick at once, so VAKYN adds no wait. The chat model's message is used, as before.
    [v, message] = await Promise.all([vakynPick(messages), chatCall(messages, { tools: TOOLS })]);
    used = "chat";
  } else {
    v = await vakynPick(messages);
    if (!v || v.confidence < MIN_CONFIDENCE) {
      [message, used] = [await chatCall(messages, { tools: TOOLS }), "chat"]; // unsure: the chat model picks
    } else if (v.pick === "none") {
      [message, used] = [await chatCall(messages), "vakyn"]; // reply in words, no tool
    } else if (v.pick === "ask_user") {
      const system = "Ask the employee one short question to learn what they need.";
      [message, used] = [await chatCall(messages, { system }), "vakyn"];
    } else {
      // pick-then-fill: offer only the picked tool and force it
      const tool = TOOLS.filter((t) => t.name === v!.pick);
      [message, used] = [await chatCall(messages, { tools: tool, toolChoice: { type: "tool", name: v.pick } }), "vakyn"];
    }
  }
  const chatPick = used === "chat" ? pickedTool(message) : null;
  log({
    request_id: v?.requestId ?? null,
    mode: MODE,
    vakyn_pick: v?.pick ?? null,
    vakyn_confidence: v?.confidence ?? null,
    vakyn_probabilities: v?.probabilities ?? null,
    chat_pick: chatPick,
    agree: v && chatPick ? v.pick === chatPick : null,
    used,
  });
  return { message, vakyn: v };
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].split("/").pop()!)) {
  const samples = [
    "Got a new phone and now I can't get my sign-in codes.",
    "The VPN keeps dropping me since this morning, is it just me?",
    "can you help",
  ];
  for (const s of samples) {
    const { message, vakyn: v } = await nextStep([{ role: "user", content: s }]);
    const shown = message ? `${pickedTool(message)}` : "skipped (--dry)";
    console.log(`${JSON.stringify(s)}\n  VAKYN: ${v?.pick} ${v?.confidence}  chat model: ${shown}`);
  }
  console.log(`log: ${LOG_PATH}`);
}
