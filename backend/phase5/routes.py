"""
Phase 5: FastAPI Route Definitions
====================================
Three POST endpoints with Pydantic-validated requests/responses.
Each endpoint wraps the corresponding Phase 3/4 pipeline.
"""

import time
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException

from backend.phase5.models import (
    PulseRequest, PulseResponse,
    ExplainerRequest, ExplainerResponse,
    DispatchRequest, DispatchResponse,
    GateStatus, DispatchResults,
)
from backend.phase3.pipeline_reviews import ReviewPulsePipeline
from backend.phase4.pipeline_fees import FeeExplainerPipeline
from backend.phase1.scraper_reviews import ReviewScraper
from backend.phase2.llm_router import LLMUnavailableError
from backend.config import get_setting

logger = logging.getLogger("routes")

router = APIRouter(prefix="/api")


# ── POST /api/pulse ──────────────────────────────────────────

@router.post("/pulse", response_model=PulseResponse)
async def generate_pulse(req: PulseRequest):
    """Generate Weekly Review Pulse (Part A)."""
    start = time.time()
    try:
        # 1. Load or scrape reviews
        scraper = ReviewScraper()
        all_reviews = await scraper.scrape()

        # 2. Apply UI filters (weeks, star_range, max_reviews)
        filtered = _apply_ui_filters(all_reviews, req)
        if not filtered:
            return PulseResponse(status="error", error="No reviews match the selected filters.")

        # 3. Run the Map-Reduce pipeline on the filtered subset
        pipeline = ReviewPulsePipeline()
        pulse_data = pipeline.run(reviews_data=filtered)

        latency = int((time.time() - start) * 1000)
        return PulseResponse(
            status="success",
            provider_used=pulse_data.get("provider_used"),
            latency_ms=latency,
            data=pulse_data,
        )

    except LLMUnavailableError as e:
        logger.error(f"LLM unavailable: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Pulse generation error: {e}", exc_info=True)
        return PulseResponse(status="error", error=str(e))


# ── POST /api/explainer ─────────────────────────────────────

@router.post("/explainer", response_model=ExplainerResponse)
async def generate_explainer(req: ExplainerRequest):
    """Generate Fee Explainer (Part B)."""
    start = time.time()
    try:
        pipeline = FeeExplainerPipeline()
        explainer_data = pipeline.run(req.asset_class)

        latency = int((time.time() - start) * 1000)
        return ExplainerResponse(
            status="success",
            provider_used=explainer_data.get("provider_used"),
            latency_ms=latency,
            data=explainer_data,
        )

    except ValueError as e:
        return ExplainerResponse(status="error", error=str(e))
    except LLMUnavailableError as e:
        logger.error(f"LLM unavailable: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Explainer generation error: {e}", exc_info=True)
        return ExplainerResponse(status="error", error=str(e))


# ── POST /api/dispatch ──────────────────────────────────────

from backend.phase7.mcp_dispatcher import MCPDispatcher

@router.post("/dispatch", response_model=DispatchResponse)
async def dispatch_content(req: DispatchRequest):
    """Dispatch generated content via MCP (Part C)."""
    start = time.time()
    try:
        dispatcher = MCPDispatcher()
        
        # Unpack Pydantic object into dictionaries for the dispatcher
        approvals = {
            "append_to_doc": req.approvals.append_to_doc,
            "create_draft": req.approvals.create_draft
        }
        
        # Call the dispatcher
        results = dispatcher.dispatch(
            content=req.content,
            content_type=req.content_type,
            approvals=approvals,
            recipients=req.recipients
        )
        
        return DispatchResponse(
            status="success",
            results=DispatchResults(
                doc=GateStatus(**results["doc"]),
                draft=GateStatus(**results["draft"])
            )
        )
    except Exception as e:
        logger.error(f"Dispatch execution failed: {e}", exc_info=True)
        return DispatchResponse(status="error", error=str(e))


# ── Internal Helpers ─────────────────────────────────────────

def _apply_ui_filters(reviews: List[Dict[str, Any]], req: PulseRequest) -> List[Dict[str, Any]]:
    """
    Applies the UI-driven filters on top of the already hard-filtered review pool.
    Filters: weeks, star_range, max_reviews.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=req.weeks)
    filtered = []

    for r in reviews:
        # Star range filter
        score = r.get("score", 0)
        if score < req.star_range_min or score > req.star_range_max:
            continue

        # Date window filter
        try:
            dt_str = r.get("date", "")
            if dt_str:
                review_dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                if review_dt.tzinfo is None:
                    review_dt = review_dt.replace(tzinfo=timezone.utc)
                if review_dt < cutoff:
                    continue
        except (ValueError, TypeError):
            pass  # Keep review if date parsing fails

        filtered.append(r)

    # Cap to max_reviews
    return filtered[: req.max_reviews]
