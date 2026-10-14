# Friction Log

## 1. Bedrock: "Operation not allowed"
- Task: Call Nova models (lite/micro/pro/2-lite) via Converse API
- Steps: Valid IAM keys, correct `us.`/`global.` inference profile IDs
- Expected: model response
- Actual: `ValidationException: Operation not allowed` for every model
- Severity: High
- Workaround: Switched LLM to Gemini
- Suggestion: Clearer error message stating the account-plan restriction

## 2. Bedrock: Claude use-case form "not authorized"
- Task: Submit Anthropic use-case details in console
- Actual: "Your account is not authorized... create a support case"; Basic Support cannot open technical cases
- Severity: High
- Suggestion: Explain required account type up front

## 3. MCP Python SDK 2.x breaking change
- Task: Run FastMCP over Streamable HTTP
- Actual: `FastMCP` renamed to `MCPServer` in mcp 2.x
- Severity: Medium
- Workaround: `pip install "mcp<2"`
- Suggestion: Update starter docs/pin versions

## 4. Django ORM inside async MCP tool
- Actual: "You cannot call this from an async context"
- Severity: Medium
- Workaround: `sync_to_async`
- Suggestion: Add docs example for sync ORMs

## 5. MCP Inspector "Session not found"
- Task: Test tools after editing server code
- Actual: Restarting server invalidates the session
- Severity: Low
- Workaround: Reconnect in Inspector

## 6. Gemini: model deprecation (404)
- Task: Call `gemini-2.5-flash` with a new API key
- Expected: model response
- Actual: 404 NOT_FOUND "no longer available to new users"
- Severity: Medium
- Workaround: Switched to a newer model listed in AI Studio
- Suggestion: List currently available model IDs in the quickstart

## 7. Gemini: free-tier quota exhausted (429)
- Task: Test tool-calling agent repeatedly
- Actual: 429 RESOURCE_EXHAUSTED, limit 20 requests/day per model; one chat question with tool calls uses several requests
- Severity: Medium
- Workaround: Switched to another model, moved some buttons to direct API calls (no LLM)
- Suggestion: Show remaining quota in AI Studio and document requests-per-tool-call