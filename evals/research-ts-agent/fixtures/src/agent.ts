import type Anthropic from "@anthropic-ai/sdk";
import { anthropic, MODEL } from "./client.js";
import { runTool } from "./handlers.js";
import { tools } from "./tools.js";

const SYSTEM = `You are the shopping assistant for Northwind Outdoor.
Use the tools to look things up or act. Never guess order details.
When you have what you need, answer the customer in two or three friendly sentences.`;

// One chat turn: the model picks tools until it can answer, then writes the reply.
export async function chatTurn(history: Anthropic.MessageParam[]): Promise<string> {
  const messages = [...history];
  for (let step = 0; step < 5; step++) {
    const res = await anthropic.messages.create({
      model: MODEL,
      max_tokens: 1024,
      system: SYSTEM,
      tools,
      tool_choice: { type: "auto" },
      messages,
    });

    const toolUses = res.content.filter((b) => b.type === "tool_use");
    if (toolUses.length === 0) {
      return res.content.map((b) => (b.type === "text" ? b.text : "")).join("");
    }

    messages.push({ role: "assistant", content: res.content });
    const results = await Promise.all(
      toolUses.map(async (t) => ({
        type: "tool_result" as const,
        tool_use_id: t.id,
        content: JSON.stringify(await runTool(t.name, t.input)),
      })),
    );
    messages.push({ role: "user", content: results });
  }
  return "Sorry, I could not finish that. A person from our team will follow up.";
}
