# 🚀 Vercel Production Deployment Guide

We have migrated the entire application (Frontend + Backend) to **Vercel**. Streamlit Cloud is no longer used, as its network architecture physically blocks REST API endpoints. By hosting both on Vercel, everything is 100% free, fast, and seamlessly unified!

Because we have a Node.js frontend and a Python backend in the same repository, we will create **two separate Vercel projects** connected to the same GitHub repository.

---

## Part 1: Deploy the Python Backend API

1. Go to your **Vercel Dashboard** and click **"Add New..." -> "Project"**.
2. Import your GitHub repository: `swayam-kr/M2_MCP_AI_Automation`.
3. In the Configuration screen:
   - **Project Name**: `groww-weekly-api` (or similar)
   - **Framework Preset**: select **Other**
   - **Root Directory**: Leave it as the default `/` (Do NOT choose `frontend`).
   - **Build Command**: Leave empty (Vercel automatically detects `api/index.py`).
   - **Output Directory**: Leave empty
4. Open the **Environment Variables** section and paste your secrets:
   ```env
   GROQ_API_KEY_1=gsk_...
   GROQ_API_KEY_2=gsk_...
   GROQ_API_KEY_3=gsk_...
   GEMINI_API_KEY=AIza...
   GOOGLE_OAUTH_CLIENT_ID=...
   GOOGLE_OAUTH_CLIENT_SECRET=...
   GOOGLE_DOCS_DOC_ID=...
   BACKEND_API_KEY=my-secret-password-123
   ```
5. Click **Deploy**.
6. When finished, copy the new URL of your backend (e.g., `https://groww-weekly-api.vercel.app`).

---

## Part 2: Deploy the Next.js Frontend UI

1. Go back to your **Vercel Dashboard** and click **"Add New..." -> "Project"**.
2. Import the exact same GitHub repository again: `swayam-kr/M2_MCP_AI_Automation`.
3. In the Configuration screen:
   - **Project Name**: `groww-weekly-ui` (or similar)
   - **Framework Preset**: select **Next.js**
   - **Root Directory**: Click "Edit" and change it to `frontend`.
4. Open the **Environment Variables** section and add:
   - `NEXT_PUBLIC_BACKEND_URL`: Paste the URL you copied from Part 1 here (e.g., `https://groww-weekly-api.vercel.app`). *No slash at the end.*
   - `BACKEND_API_KEY`: `my-secret-password-123` (Must match Part 1 exactly)
5. Click **Deploy**.

---

## Part 3: Adding Google OAuth Token (for Dispatchers)
Because Vercel is stateless, it needs the `token.json` to post to Google Docs/Gmail on your behalf without asking for a browser login every week.

1. On your local machine, ensure you have ran the scraper locally once so the `token.json` file is generated in the root folder.
2. Open terminal and run:
   ```bash
   cat token.json
   ```
3. Copy the entire JSON printed.
4. Go to **Vercel Dashboard** -> Your `groww-weekly-api` (Backend) Project -> **Settings** -> **Environment Variables**.
5. Add a new variable:
   - **Key**: `GOOGLE_TOKEN_JSON`
   - **Value**: Paste the entire JSON you copied.
6. Go to **Deployments** -> Click the `...` next to the latest -> **Redeploy**.

> **Note:** Do NOT commit `token.json` to GitHub! Setting it as an environment variable keeps your Google Account 100% secure.

🎉 **All done! Your full-stack AI platform is now live entirely on Vercel.**
