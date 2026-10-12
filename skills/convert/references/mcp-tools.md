# Read an MCP server's tool list

Where to find it: the result of a `tools/list` call. In code: `await session.list_tools()` (Python
`mcp`), `await client.listTools()` (TypeScript `@modelcontextprotocol/sdk`). Without code, ask the
person to save the output of their client's tool listing, or read the server's source where tools
are registered (`@mcp.tool()`, `server.tool(...)`, `registerTool(...)`).

## Shape

```json
{"jsonrpc": "2.0", "id": 2, "result": {"tools": [
  {"name": "create_issue", "title": "Create issue",
   "description": "Create a new issue with a title, description and optional labels.",
   "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}}},
   "annotations": {"readOnlyHint": false}}
], "nextCursor": "..."}}
```

## Read

| Option field | From |
|---|---|
| name | `name` (keep the exact string; it is what `tools/call` needs) |
| description | `description`, rewritten to one line; use `title` when there is no description |
| ignored | `inputSchema`, `outputSchema`, `annotations` |

- **Paged lists.** If the result has `nextCursor`, call `tools/list` again with that cursor until
  it is gone. Convert the full list.
- **Several servers.** Prefix each option with its server (`tracker__create_issue`,
  `docs__search`) and keep a table from option to `(server, tool name)`. Clashing names are common
  (`search`, `list`). Many servers or more than 255 tools: use the server as the group in a
  [two-stage pick](tool-pick.md#more-than-255-tools-two-stages).
- **Tools change.** Servers can add tools at run time (`notifications/tools/list_changed`). Build
  the options from the live list at start-up and when that notice arrives, not from a copy pasted
  into code. New tools still need a one-line description; flag the ones with none.

Sample: [tracker-tools.mcp.json](../examples/tracker-tools.mcp.json) →
[tracker-tools.request.json](../examples/tracker-tools.request.json).

## Fill one tool

The app's chat model usually sees MCP tools converted to its own format (OpenAI or Anthropic).
Fill the picked tool the same way: offer only that tool, forced, and send the arguments it returns
with `tools/call`:

```python
result = await session.call_tool(pick, arguments=args)
```
