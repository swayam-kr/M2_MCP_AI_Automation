"""
Phase 5: FastAPI Application Entry Point
==========================================
Initializes the FastAPI app with CORS, logging middleware,
startup events, and mounts the API router.
"""

import os
import sys
import time
import logging

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_setting
from backend.phase5.routes import router

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, get_setting("app.log_level", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

# ── App Initialization ───────────────────────────────────────
app = FastAPI(
    title=get_setting("app.name", "AI Ops Automator"),
    version=get_setting("app.version", "3.0"),
    description="AI-powered weekly review pulse and fee explainer for Groww.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS Middleware ──────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Dev mode — restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request Logging Middleware ───────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration_ms}ms)")
    return response

@app.middleware("http")
async def api_key_validation(request: Request, call_next):
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"] or request.method == "OPTIONS":
        return await call_next(request)
        
    expected_key = os.getenv("BACKEND_API_KEY")
    if expected_key:
        provided_key = request.headers.get("X-API-KEY")
        if not provided_key or provided_key != expected_key:
            return JSONResponse(
                status_code=401, 
                content={"status": "error", "error": "Unauthorized: Invalid or missing X-API-KEY"}
            )
            
    return await call_next(request)

# ── Startup Events ───────────────────────────────────────────

@app.on_event("startup")
async def startup_checks():
    """Verify critical configuration on startup."""
    missing = []
    if not os.getenv("GROQ_API_KEY_1"):
        missing.append("GROQ_API_KEY_1")
    if not os.getenv("GEMINI_API_KEY"):
        missing.append("GEMINI_API_KEY")

    if missing:
        logger.warning(f"⚠️  Missing API keys: {', '.join(missing)}. Some features may fail.")
    else:
        logger.info("✅ All required API keys are present.")

    logger.info(f"🚀 {get_setting('app.name')} v{get_setting('app.version')} started successfully.")

# ── Global Error Handler ─────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "error": "Internal server error. Check server logs."},
    )

# ── Mount Router ─────────────────────────────────────────────
app.include_router(router)

# ── Health Check ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": get_setting("app.version", "3.0")}
