import { anthropic, MODEL_SMALL } from "./client.js";

const RULES = `You moderate product reviews for Northwind Outdoor.
Reject a review if it contains insults, personal data (phone, email, address), links,
or is about shipping rather than the product. Otherwise approve it.
Answer with exactly one word: APPROVE or REJECT.`;

// Runs on every submitted review before it is shown on the product page.
export async function moderateReview(review: string): Promise<boolean> {
  const res = await anthropic.messages.create({
    model: MODEL_SMALL,
    max_tokens: 5,
    system: RULES,
    messages: [{ role: "user", content: review }],
  });
  const text = res.content[0].type === "text" ? res.content[0].text.trim().toUpperCase() : "";
  return text === "APPROVE";
}
