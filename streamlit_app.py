"""
Streamlit Cloud Entry Point
===========================
This thin wrapper launches the FastAPI backend via Uvicorn.
Streamlit Cloud requires a Streamlit entry point, but we use it
only to bootstrap the real FastAPI server.
"""

import streamlit as st
import subprocess
import threading
import time
import os


def run_uvicorn():
    """Launch FastAPI in a background thread."""
    port = os.getenv("PORT", "8000")
    subprocess.run([
        "uvicorn", "backend.phase5.main:app",
        "--host", "0.0.0.0",
        "--port", port,
        "--workers", "1"
    ])


# Start Uvicorn in background
server_thread = threading.Thread(target=run_uvicorn, daemon=True)
server_thread.start()
time.sleep(3)  # Wait for server to boot

# Streamlit admin dashboard
st.set_page_config(page_title="Groww Weekly Digest — Backend", page_icon="📊")
st.title("📊 Groww Weekly Digest — Backend")
st.success("✅ FastAPI server is running on port 8000")
st.markdown("---")

st.subheader("Health Check")
try:
    import requests
    resp = requests.get(f"http://localhost:{os.getenv('PORT', '8000')}/health", timeout=5)
    st.json(resp.json())
except Exception as e:
    st.error(f"Health check failed: {e}")

st.subheader("Configuration")
st.code(f"""
API Keys Loaded:
  GROQ_API_KEY_1: {'✅' if os.getenv('GROQ_API_KEY_1') else '❌'}
  GROQ_API_KEY_2: {'✅' if os.getenv('GROQ_API_KEY_2') else '❌'}
  GROQ_API_KEY_3: {'✅' if os.getenv('GROQ_API_KEY_3') else '❌'}
  GEMINI_API_KEY: {'✅' if os.getenv('GEMINI_API_KEY') else '❌'}
  GOOGLE_OAUTH: {'✅' if os.getenv('GOOGLE_OAUTH_CLIENT_ID') else '❌'}
  GOOGLE_DOCS_DOC_ID: {'✅' if os.getenv('GOOGLE_DOCS_DOC_ID') else '❌'}
""")
