// Calls into the shop's own services. No chat-model calls in this file.
export async function runTool(name: string, input: unknown): Promise<unknown> {
  switch (name) {
    case "search_products":
    case "get_order_status":
    case "start_return":
    case "update_address":
    case "apply_coupon":
    case "talk_to_human":
      return { ok: true, tool: name, input };
    default:
      return { ok: false, error: `unknown tool ${name}` };
  }
}
