import type Anthropic from "@anthropic-ai/sdk";

export const tools: Anthropic.Tool[] = [
  {
    name: "search_products",
    description: "Search the catalog by keywords, category or price range.",
    input_schema: {
      type: "object",
      properties: { query: { type: "string" }, max_price: { type: "number" } },
      required: ["query"],
    },
  },
  {
    name: "get_order_status",
    description: "Look up where an order is and when it will arrive.",
    input_schema: {
      type: "object",
      properties: { order_id: { type: "string" } },
      required: ["order_id"],
    },
  },
  {
    name: "start_return",
    description: "Open a return for one item of a delivered order.",
    input_schema: {
      type: "object",
      properties: { order_id: { type: "string" }, sku: { type: "string" }, reason: { type: "string" } },
      required: ["order_id", "sku"],
    },
  },
  {
    name: "update_address",
    description: "Change the delivery address of an order that has not shipped.",
    input_schema: {
      type: "object",
      properties: { order_id: { type: "string" }, address: { type: "string" } },
      required: ["order_id", "address"],
    },
  },
  {
    name: "apply_coupon",
    description: "Apply a coupon code to the customer's cart.",
    input_schema: {
      type: "object",
      properties: { code: { type: "string" } },
      required: ["code"],
    },
  },
  {
    name: "talk_to_human",
    description: "Hand the conversation to a person on the support team.",
    input_schema: {
      type: "object",
      properties: { summary: { type: "string" } },
      required: ["summary"],
    },
  },
];
