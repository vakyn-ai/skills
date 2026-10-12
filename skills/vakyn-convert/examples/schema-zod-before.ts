// BEFORE: marketplace listing review with a Zod schema and the Vercel AI SDK's generateObject.
//
// The chat model fills the whole object: a decision, a list of issues, a nested seller check, a
// 1-4 rating, and a rewritten title. schema_zod_after.ts is the same app after the conversion.
//
// npm install ai @ai-sdk/openai zod
import { openai } from "@ai-sdk/openai";
import { generateObject } from "ai";
import { z } from "zod";

export const ListingReview = z.object({
  decision: z
    .enum(["approve", "needs_edit", "reject"])
    .describe("approve: can go live as is. needs_edit: allowed, but the seller must fix the text. reject: not allowed on the market."),
  issues: z
    .array(z.enum(["prohibited_item", "misleading_price", "contact_details", "missing_condition"]))
    .describe("Every problem in the listing text. Empty when there is none."),
  seller: z.object({
    looks_like_business: z.boolean().describe("True when the text reads like a shop or trader, not a private person."),
  }),
  quality: z.number().int().min(1).max(4).describe("How well the text describes the item: 1 = poor, 4 = excellent."),
  suggested_title: z.string().describe("A clear title of at most 60 characters."),
});
export type ListingReview = z.infer<typeof ListingReview>;

export async function reviewListing(listingText: string): Promise<ListingReview> {
  const { object } = await generateObject({
    model: openai("gpt-4.1-mini"),
    schema: ListingReview,
    prompt: `Review this listing for Swapyard, a second-hand marketplace.\n\n${listingText}`,
  });
  return object;
}
