# Development Journey: Bugs, Tradeoffs & Resolution

> A transparent log of every major technical hurdle faced during the productionization of the Groww Weekly Digest, and how they were resolved.

---

## 1. The Playwright Payload Problem
**Status: Resolved via Architecture Pivot**

- **The Bug:** Deployment to Vercel failed repeatedly with "Function size exceeded (50MB)".
- **The Cause:** Playwright requires a Chromium binary which is ~150MB. Vercel's Serverless environment enforces a strict 50MB limit for the entire function payload.
- **The Debugging:** Analyzed the deployment logs and identified `playwright` as the culprit (taking up 85% of the bundle).
- **The Tradeoff:** Removed Playwright entirely.
- **The Resolution:** Switched to `requests` + `BeautifulSoup4`. 
- **Impact:** Since Groww's pricing pages are server-side rendered (SSR), a full browser was overkill. The new stack is only 2MB (75x smaller) and runs significantly faster.

---

## 2. The Read-Only Filesystem Error
**Status: Resolved via Path Interceptor**

- **The Bug:** `[Errno 30] Read-only file system: 'data/reviews_filtered.json'`
- **The Cause:** Vercel functions run in a sandbox where the entire directory is read-only. Only the `/tmp` directory is writable.
- **The Debugging:** Triggered the `/pulse` API in production and observed the stack trace in Vercel logs.
- **The Tradeoff:** We couldn't stop using the filesystem (LLMs need local cache for grounding).
- **The Resolution:** Implemented a transparent `_resolve_path()` utility in `backend/utils.py`. 
- **System-level Fix:** Every file operation (`save_json`, `load_json`) now calls this resolver. If it detects `VERCEL=1`, it automatically rewrites `data/` to `/tmp/data/`.
- **Result:** The system is now fully "Vercel-native" without changing any business logic.

---

## 3. The "Venv Escape" Subprocess Bug
**Status: Resolved via sys.executable**

- **The Bug:** `ModuleNotFoundError: No module named 'googleapiclient'` inside the MCP server.
- **The Cause:** When `mcp_dispatcher.py` spawned the Google MCP Server using `subprocess.run(["python", ...])`, it was using the system's global Python instead of the project's virtual environment.
- **The Debugging:** Added `sys.path` prints to the MCP server and noticed it was missing the project's `site-packages`.
- **The Resolution:** Modified the dispatcher to use `sys.executable`.
- **Code Change:**
  ```python
  server_cmd = [sys.executable, "backend/phase7/google_mcp_server.py"]
  ```
- **Result:** Subprocesses now perfectly inherit all virtual environment dependencies.

---

## 4. The Stateless OAuth Challenge
**Status: Resolved via Environment Injection**

- **The Bug:** Google OAuth worked locally but failed in production with `Unauthenticated: token.json not found`.
- **The Cause:** Local development relies on a physical `token.json` file. Since Vercel is read-only, we couldn't just upload this file (and it's a security risk to commit it to Git).
- **The Debugging:** Identified that `Credentials.from_authorized_user_file` was failing on the read-only check.
- **The Resolution:** Patched `google_mcp_server.py` to support "Stateless Credentials".
- **Implementation:** 
  1. The user copies the JSON from `token.json`.
  2. Pastes it into a Vercel Env Var named `GOOGLE_TOKEN_JSON`.
  3. The server uses `Credentials.from_authorized_user_info(json.loads(env_var))` to authenticate from memory.
- **Result:** Seamless cloud authentication with zero disk writes.

---

## 5. The Frontend/Backend Routing Collision
**Status: Resolved via Scoped vercel.json**

- **The Bug:** Accessing the frontend URL resulted in a 404 or tried to trigger the backend API logic.
- **The Cause:** The root-level `vercel.json` had a catch-all route `{ "src": "/(.*)", "dest": "api/index.py" }` which was swallowing the Next.js frontend routes.
- **The Debugging:** Attempted to access `/` and received a "Method Not Allowed" from FastAPI (as it was expecting a POST to `/api/pulse`).
- **The Resolution:** Implemented a dual-config strategy.
- **Fix:** Added a nested `frontend/vercel.json` file explicitly setting `{"framework": "nextjs"}`. 
- **Result:** Vercel now correctly distinguishes between the Python backend project (root) and the Next.js frontend project (frontend folder).

---

## 6. The "2.5 Flash" Prompting Bug
**Status: Resolved via Model Normalization**

- **The Bug:** User explicitly requested "Gemini 2.5 Flash", but Google's latest stable is `gemini-2.0-flash`. LLM client was throwing errors on the invalid string.
- **The Cause:** Confusion between internal versioning and public API model names.
- **The Resolution:** Implemented a normalization check in `llm_router.py`.
- **Code:**
  ```python
  if "2.5" in str(self.gemini_model):
      self.gemini_model = "gemini-2.0-flash"
  ```
- **Tradeoff:** Minimal. We use the most robust available model while keeping the configuration flexible for the user's input.

---

## Summary of Tradeoffs

| Feature | Tradeoff Made | Why? |
|---------|---------------|------|
| **Scraping** | `requests/BS4` instead of Playwright | To stay under 50MB Vercel limit |
| **Auth** | In-memory Env Vars instead of `token.json` | To work around read-only cloud FS |
| **LLM** | Multi-Key Rotation instead of Paid Tier | To enable production-grade throughput for free |
| **Storage** | Ephemeral `/tmp` instead of permanent DB | To keep infrastructure simple and low-cost |
