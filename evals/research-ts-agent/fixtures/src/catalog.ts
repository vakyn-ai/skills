import { anthropic, MODEL } from "./client.js";

export interface Product {
  name: string;
  category: string;
  specs: Record<string, string>;
}

// Used by the merchandising team when they add a product to the catalog.
export async function writeDescription(p: Product): Promise<string> {
  const res = await anthropic.messages.create({
    model: MODEL,
    max_tokens: 400,
    system: "Write a product page description: one short paragraph, then three bullet points. Warm, concrete, no hype.",
    messages: [{ role: "user", content: JSON.stringify(p) }],
  });
  return res.content[0].type === "text" ? res.content[0].text : "";
}
