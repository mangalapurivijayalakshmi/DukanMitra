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

## 6. Gemini model deprecations and free quota
- `gemini-2.5-flash` returned 404 for new users; free tier allowed only 20 requests/day on one model
- Severity: Medium
- Workaround: Switched to `gemini-3.5-flash-lite`