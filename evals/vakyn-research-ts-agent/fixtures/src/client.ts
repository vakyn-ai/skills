import Anthropic from "@anthropic-ai/sdk";

export const anthropic = new Anthropic(); // reads ANTHROPIC_API_KEY
export const MODEL = process.env.SHOP_MODEL ?? "claude-sonnet-4-5";
export const MODEL_SMALL = process.env.SHOP_MODEL_SMALL ?? "claude-haiku-4-5";
