# Groww Weekly Digest — API & Protocol Reference

> Complete reference for every API endpoint, the MCP JSON-RPC protocol, LLM orchestration internals, and authentication flows.

---

## Table of Contents

| # | Section |
|---|---------|
| 1 | [REST API Endpoints](#1-rest-api-endpoints) |
| 2 | [Next.js Proxy Layer](#2-nextjs-proxy-layer) |
| 3 | [MCP JSON-RPC Protocol](#3-mcp-json-rpc-protocol) |
| 4 | [LLM Orchestration Engine](#4-llm-orchestration-engine) |
| 5 | [OAuth2 Authentication](#5-oauth2-authentication) |
| 6 | [Error Codes & Troubleshooting](#6-error-codes--troubleshooting) |

---

## 1. REST API Endpoints

**Base URL:** `https://groww-weekly-api.vercel.app` (production) or `http://localhost:8000` (local)

**Authentication:** All endpoints (except `/health`) require `X-API-KEY` header matching the `BACKEND_API_KEY` environment variable.

---

### `GET /health`

Health check — no authentication required.

**Response:**
```json
{"status": "ok", "version": "3.0"}
```

---

### `POST /api/pulse`

Generates the Weekly Review Pulse — scrapes Play Store reviews, applies user filters, runs Map-Reduce LLM analysis.

**Request:**
```json
{
  "weeks": 4,
  "max_reviews": 100,
  "star_range_min": 1,
  "star_range_max": 3
}
```

| Field | Type | Range | Default | Description |
|-------|------|-------|---------|-------------|
| `weeks` | int | 1–8 | 4 | How many weeks of reviews to analyze |
| `max_reviews` | int | 10–200 | 100 | Maximum reviews after filtering |
| `star_range_min` | int | 1–5 | 1 | Minimum star rating to include |
| `star_range_max` | int | 1–5 | 5 | Maximum star rating to include |

**cURL Example:**
```bash
curl -X POST https://groww-weekly-api.vercel.app/api/pulse \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your-secret-key" \
  -d '{"weeks": 4, "max_reviews": 100, "star_range_min": 1, "star_range_max": 3}'
```

**Success Response (200):**
```json
{
  "status": "success",
  "provider_used": "gemini",
  "latency_ms": 12450,
  "data": {
    "generated_at": "2026-03-27T00:15:00Z",
    "provider_used": "gemini",
    "period": "Feb 27 - Mar 27",
    "analysis_explanation": "This analysis is based on 87 reviews...",
    "total_reviews_analyzed": 87,
    "themes": [
      {"name": "App Crashes", "review_count": 23, "percentage": 26.4, "average_rating": 1.2}
    ],
    "top_3_themes": ["App Crashes", "Slow Loading", "Poor Support"],
    "quotes": [
      {"text": "Every time I try to pay, the app freezes.", "star_rating": 1, "date": "2026-03-18"}
    ],
    "summary": "Over the past 4 weeks, analysis reveals...",
    "action_ideas": ["Prioritize payment gateway stability.", "Add skeleton loading screens.", "Audit MF selection flow."]
  }
}
```

**Internal Execution Flow:**
1. `ReviewScraper().scrape()` — fetches/caches reviews
2. `_apply_ui_filters()` — applies weeks, star range, and max_reviews caps
3. `ReviewPulsePipeline().run(reviews_data=filtered)` — Map-Reduce LLM pipeline
4. Return structured response

---

### `POST /api/explainer`

Generates the Fee Structure Explainer for a given asset class.

**Request:**
```json
{
  "asset_class": "Stocks"
}
```

| Field | Type | Allowed | Description |
|-------|------|---------|-------------|
| `asset_class` | string | `"Stocks"`, `"F&O"`, `"Mutual Funds"` | Which asset class to explain |

**cURL Example:**
```bash
curl -X POST https://groww-weekly-api.vercel.app/api/explainer \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your-secret-key" \
  -d '{"asset_class": "Stocks"}'
```

**Success Response (200):**
```json
{
  "status": "success",
  "provider_used": "gemini",
  "latency_ms": 3200,
  "data": {
    "generated_at": "2026-03-27T00:20:00Z",
    "asset_class": "Stocks",
    "explanation_bullets": [
      "Groww charges a flat brokerage of ₹20 per order or 0.05%, whichever is lower.",
      "STT of 0.025% is levied on the sell side.",
      "Exchange transaction charges: NSE 0.00297%, BSE 0.00300%.",
      "GST at 18% on brokerage + exchange charges.",
      "SEBI turnover fee: ₹10 per crore.",
      "Stamp duty varies by state, on buy-side."
    ],
    "official_links": ["https://groww.in/pricing"],
    "last_checked": "2026-03-24T00:00:00Z",
    "tone": "neutral",
    "provider_used": "gemini"
  }
}
```

**Internal Execution Flow:**
1. `FeeScraper().scrape()` — fetches/caches fee data
2. `FeeExplainerPipeline().run(asset_class)` — KB-grounded LLM generation
3. Anti-hallucination validation (strip LLM URLs, append real ones)
4. Return structured response

---

### `POST /api/dispatch`

Dispatches generated content to Google Docs and/or Gmail via MCP.

**Request:**
```json
{
  "content_type": "combined",
  "content": {
    "pulse": { "data": { "...pulse JSON..." } },
    "explainer": { "data": { "...explainer JSON..." } }
  },
  "approvals": {
    "append_to_doc": true,
    "create_draft": false
  },
  "recipients": ["team@example.com"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `content_type` | string | `"pulse"`, `"explainer"`, or `"combined"` |
| `content` | object | Raw JSON from pulse/explainer endpoints |
| `approvals.append_to_doc` | bool | Gate 1: Append to Google Doc |
| `approvals.create_draft` | bool | Gate 2: Create Gmail draft |
| `recipients` | string[] | Email addresses for draft (required if create_draft is true) |

**cURL Example:**
```bash
curl -X POST https://groww-weekly-api.vercel.app/api/dispatch \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your-secret-key" \
  -d '{
    "content_type": "pulse",
    "content": {"summary": "...", "themes": []},
    "approvals": {"append_to_doc": true, "create_draft": false},
    "recipients": []
  }'
```

**Success Response (200):**
```json
{
  "status": "success",
  "results": {
    "doc": {"status": "appended", "error": null},
    "draft": {"status": "skipped", "error": null}
  }
}
```

**Gate Status Values:**

| Status | Meaning |
|--------|---------|
| `"appended"` | Successfully written to Google Doc |
| `"created"` | Gmail draft created |
| `"skipped"` | Gate was OFF (user did not approve) |
| `"error"` | Failed — check `error` field for details |

---

## 2. Next.js Proxy Layer

The frontend never calls the FastAPI backend directly. Three Next.js API routes act as authenticated proxies:

| Frontend Route | Backend Target | What It Adds |
|-------------|----------------|-------------|
| `/api/pulse` | `${NEXT_PUBLIC_BACKEND_URL}/api/pulse` | `X-API-KEY` header |
| `/api/explainer` | `${NEXT_PUBLIC_BACKEND_URL}/api/explainer` | `X-API-KEY` header |
| `/api/dispatch` | `${NEXT_PUBLIC_BACKEND_URL}/api/dispatch` | `X-API-KEY` header |

**Example proxy logic (simplified):**
```typescript
export async function POST(request: Request) {
  const body = await request.json();
  const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/pulse`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-KEY": process.env.BACKEND_API_KEY || ""
    },
    body: JSON.stringify(body)
  });
  return Response.json(await res.json());
}
```

**Why proxy instead of direct calls?**
1. **Security:** `BACKEND_API_KEY` stays on the server — never exposed to the browser
2. **CORS:** Browser-to-backend cross-origin issues are eliminated entirely
3. **Flexibility:** Backend URL can change without any frontend code changes

---

## 3. MCP JSON-RPC Protocol

### What is MCP?

**Model Context Protocol (MCP)** is a standardized way for AI systems to invoke external tools. In this project, it's implemented as a **JSON-RPC 2.0 server communicating over stdin/stdout pipes**.

### How It Actually Works (Step by Step)

1. **FastAPI receives dispatch request** → calls `MCPDispatcher.dispatch()`
2. **Dispatcher formats content** → converts raw JSON to icon-rich text via `format_pulse_for_dispatch()`
3. **Dispatcher spawns subprocess** → `subprocess.run(["python", "google_mcp_server.py"], input=payload, capture_output=True)`
4. **Subprocess reads stdin** → parses two JSON-RPC messages (initialize + tools/call)
5. **Subprocess calls Google API** → using OAuth2 credentials
6. **Subprocess writes stdout** → JSON-RPC response with result or error
7. **Dispatcher parses stdout** → extracts result, returns to FastAPI

### JSON-RPC Message Format

**Message 1 — Initialize (Handshake):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "ai-ops-automator", "version": "3.0"}
  }
}
```

**Message 2 — Tool Call:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "documents.appendText",
    "arguments": {
      "document_id": "1abc...xyz",
      "text": "📊 **WeeklyProductPulse — Groww**\n..."
    }
  }
}
```

**Success Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [{"type": "text", "text": "success"}]
  }
}
```

**Error Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "error": {
    "code": -32000,
    "message": "Error: Unauthenticated. Reason: token.json not found"
  }
}
```

### Available MCP Tools

| Tool Name | Google API | What It Does |
|-----------|-----------|-------------|
| `documents.appendText` | `docs.documents().batchUpdate()` | Inserts a page break + text at the end of a Google Doc |
| `gmail.createDraft` | `gmail.users().drafts().create()` | Creates an email draft with to/subject/body |

### Google Docs Append — Technical Detail

The append logic dynamically finds the document's end index:

```python
doc = service.documents().get(documentId=doc_id).execute()
end_index = doc['body']['content'][-1]['endIndex'] - 1

requests = [
    {'insertPageBreak': {'location': {'index': end_index}}},
    {'insertText': {'location': {'index': end_index + 1}, 'text': text + "\n\n"}}
]
service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
```

This ensures each new report appears on a new page, appended chronologically.

### Virtual Environment Inheritance

The dispatcher uses `sys.executable` instead of hardcoded `python3` to launch the subprocess:

```python
doc_cmd = get_setting("mcp.google_docs.server_command").split()
if doc_cmd[0] in ("python", "python3"):
    doc_cmd[0] = sys.executable  # e.g., /path/to/venv/bin/python
```

This ensures subprocesses inherit the active virtual environment with all installed dependencies.

---

## 4. LLM Orchestration Engine

### Provider Strategy

| Task Type | Primary Provider | Fallback | Why |
|-----------|-----------------|----------|-----|
| **Classification** (theme extraction) | Groq (llama-3.3-70b, 3 keys) | — | Fast, cheap, parallelizable |
| **Generation** (summaries, explanations) | Gemini 2.0 Flash | Groq | Higher reasoning quality, larger context window |

### Multi-Key Rotation Algorithm

```
Request 1 → Key 1
Request 2 → Key 2
Request 3 → Key 3
Request 4 → Key 1 (wraps around)

If Key 1 returns 429:
  → Immediately retry with Key 2
  → If Key 2 also 429, retry with Key 3
  → If all fail, raise LLMUnavailableError
```

### Map-Reduce Architecture

**When it triggers:** When the total review text exceeds 67% of Groq's 8,192-token context window.

**Map Phase:**
- Reviews split into chunks of ~50
- Each chunk sent to a **different Groq key** via `ThreadPoolExecutor`
- Each chunk returns `{themes: [{name, review_count, avg_rating}]}`
- Up to 4 chunks processed concurrently

**Reduce Phase:**
- All themes merged by name (sum counts, weighted average ratings)
- Top 10 themes + 150 worst-rated raw reviews sent to **Gemini**
- Gemini returns: top 3 themes, 3 quotes, summary, 3 action ideas

### Token Budget Management

```python
available = context_window * 0.67  # Reserve 33% for output
estimated = len(text) // 4         # ~4 chars per token
fits = estimated < available
```

If the input doesn't fit, it's automatically chunked. The 67% ratio is configurable via `llm.routing.token_budget_ratio`.

---

## 5. OAuth2 Authentication

### One-Time Token Generation (Local)

```bash
python -m backend.phase7.auth
```

This opens a browser window for Google consent. After granting Docs + Gmail scopes, a `token.json` file is saved containing:

| Field | Purpose |
|-------|---------|
| `token` | Short-lived access token (~60 min) |
| `refresh_token` | Long-lived token for automatic renewal |
| `client_id` | OAuth application identity |
| `client_secret` | OAuth application secret |
| `scopes` | `documents` + `gmail.compose` |

### Stateless Cloud Authentication (Vercel)

Since Vercel's filesystem is read-only, `token.json` can't exist as a file. Instead:

1. The entire contents of `token.json` are pasted into Vercel's `GOOGLE_TOKEN_JSON` environment variable
2. The MCP server reads this variable at startup
3. `Credentials.from_authorized_user_info(json.loads(token_env))` constructs credentials in memory
4. The `refresh_token` automatically renews the access token when it expires

### OAuth Scopes

| Scope | Permission |
|-------|-----------|
| `googleapis.com/auth/documents` | Read/write Google Docs (append text only) |
| `googleapis.com/auth/gmail.compose` | Create drafts (cannot read inbox or delete) |

---

## 6. Error Codes & Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `401: Invalid or missing X-API-KEY` | Frontend not sending API key, or key mismatch | Check `BACKEND_API_KEY` matches in both Vercel projects |
| `[Errno 30] Read-only file system` | Trying to write to `data/` on Vercel | Ensure `utils.py` has `_resolve_path()` routing to `/tmp` |
| `Unauthenticated: GOOGLE_TOKEN_JSON env var missing` | OAuth env var not set in Vercel | Add `GOOGLE_TOKEN_JSON` in Vercel Settings → Environment Variables |
| `ModuleNotFoundError` in MCP subprocess | Subprocess using system Python instead of venv | Ensure `sys.executable` is used in `mcp_dispatcher.py` |
| `429 Rate Limit` from Groq | API key quota exhausted | System auto-rotates to next key; add more keys if persistent |
| `Missing input KB file: data/fee_kb.json` | Fee scraper not invoked before pipeline | Ensure `FeeScraper().scrape()` is called in `/explainer` route |
| `404: NOT_FOUND` on frontend URL | Vercel built backend config instead of Next.js | Set Root Directory to `frontend` in Vercel project settings |
