# Deployment Guide — Groww Weekly Digest

## Prerequisites
- GitHub account with repo access
- Vercel account (free tier works)
- Streamlit Cloud account (free tier works)
- Google Cloud OAuth credentials (already set up if `token.json` exists)

---

## Step 1: Push to GitHub

```bash
cd /Users/kumarswayam/Desktop/M2_MCP_AI_Automation

# Initialize (if not done)
git init
git remote add origin https://github.com/YOUR_USERNAME/M2_MCP_AI_Automation.git

# Stage and commit
git add -A
git commit -m "Production release: Groww Weekly Digest v4.0"

# Push
git push -u origin main
```

> **Important:** Verify `.gitignore` excludes `token.json`, `.env`, `data/*.json`, `node_modules/`, and `venv/`.

---

## Step 2: Deploy Frontend to Vercel (Fresh Start)

1.  **Delete Existing Project**: Go to **Settings > General** and scroll to the bottom to delete the old project (this clears all "ghost" settings).
2.  **New Project**: Go to [vercel.com/new](https://vercel.com/new) and import the repository.
3.  **Project Name**: `groww-weekly-digest`.
4.  **Root Directory**: Leave this as the **default** (this should be the main repo folder, **NOT** the `frontend` folder).
5.  **Build & Output Settings**: (Toggle all 3 to **ON** and paste these commands):
    - **Install Command**: `cd frontend && npm install`
    - **Build Command**: `cd frontend && npm install && npm run build`
    - **Output Directory**: `frontend/.next`
6.  **Environment Variables**:
    - **Key**: `NEXT_PUBLIC_BACKEND_URL`
    - **Value**: `https://m2-groww-weekly-digest.streamlit.app`
7.  Click **"Deploy"**.

**After deploy:** Note down your Vercel URL (e.g., `https://groww-digest.vercel.app`).

---

## Step 3: Deploy Backend to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and connect your GitHub repo.
2. Set **Main file** to `streamlit_app.py`.
3. Add **Secrets** (equivalent of `.env`):
   ```toml
   GROQ_API_KEY_1 = "your-key-1"
   GROQ_API_KEY_2 = "your-key-2"
   GROQ_API_KEY_3 = "your-key-3"
   GEMINI_API_KEY = "your-gemini-key"
   GOOGLE_OAUTH_CLIENT_ID = "your-client-id"
   GOOGLE_OAUTH_CLIENT_SECRET = "your-client-secret"
   GOOGLE_DOCS_DOC_ID = "your-doc-id"
   ```
4. Click **Deploy**.

> **Note:** `token.json` must be generated locally first (via `python -m backend.phase7.auth`) and committed to a private repo branch or managed via secrets. Streamlit Cloud cannot run interactive OAuth flows.

---

## Step 4: Connect Frontend ↔ Backend

1. Update your Vercel env var `NEXT_PUBLIC_BACKEND_URL` with the Streamlit Cloud URL.
2. Redeploy Vercel: `vercel --prod` or push a commit.
3. Test the connection by generating a pulse from the Vercel-hosted frontend.

---

## Step 5: Verify Production

| Check | How |
|-------|-----|
| Backend health | Visit `https://YOUR-BACKEND.streamlit.app` — should show admin dashboard |
| Frontend loads | Visit `https://YOUR-FRONTEND.vercel.app` — should show Groww Weekly Digest UI |
| Pulse generation | Click "Generate Pulse" — should return analysis |
| Doc append | Toggle "Append to Doc" and dispatch — check your Google Doc |
| Email draft | Toggle "Create Draft" and dispatch — check Gmail Drafts folder |

---

## Alternative: Deploy Backend on Render (if Streamlit Cloud has issues)

1. Create `Procfile`:
   ```
   web: uvicorn backend.phase5.main:app --host 0.0.0.0 --port $PORT
   ```
2. Push to Render from GitHub.
3. Set all env vars in the Render dashboard.
4. Update Vercel `NEXT_PUBLIC_BACKEND_URL` to your Render URL.
