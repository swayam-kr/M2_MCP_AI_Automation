"""
Tests for Phase 5: FastAPI Backend
====================================
Uses httpx AsyncClient + pytest-asyncio to test all 3 endpoints.
All LLM/scraper calls are mocked to avoid real API hits.
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport

from backend.phase5.main import app
from backend.phase5.models import PulseRequest, ExplainerRequest
from backend.phase2.llm_router import LLMResponse


# ── Fixtures ─────────────────────────────────────────────────

@pytest.fixture
def mock_reviews():
    """Sample reviews matching the Phase 1 output schema."""
    return [
        {"content": "This app is terrible, so many glitches and lag in trading.", "score": 1, "date": "2026-03-20T00:00:00+00:00"},
        {"content": "Really great app for investing money in stocks and mutual funds.", "score": 5, "date": "2026-03-21T00:00:00+00:00"},
        {"content": "Brokerage charges are way too high compared to other platforms.", "score": 2, "date": "2026-03-22T00:00:00+00:00"},
        {"content": "The customer support is absolutely useless and never responds.", "score": 1, "date": "2026-03-19T00:00:00+00:00"},
        {"content": "I love the dark mode and the user interface is very clean.", "score": 4, "date": "2026-03-18T00:00:00+00:00"},
    ] * 20  # 100 reviews

@pytest.fixture
def mock_pulse_output():
    return {
        "generated_at": "2026-03-25T00:00:00Z",
        "provider_used": "groq",
        "period": "Processed 100 recent reviews",
        "total_reviews_analyzed": 100,
        "themes": [{"name": "Technical Issues", "review_count": 40}],
        "top_3_themes": ["Technical Issues", "High Charges", "Poor Support"],
        "quotes": [
            {"text": "So many glitches", "star_rating": 1, "date": "2026-03-20"},
            {"text": "Charges too high", "star_rating": 2, "date": "2026-03-22"},
            {"text": "Support useless", "star_rating": 1, "date": "2026-03-19"},
        ],
        "summary": "Users are unhappy with glitches and high fees.",
        "action_ideas": ["Fix glitches", "Lower fees", "Improve support"],
    }

@pytest.fixture
def mock_explainer_output():
    return {
        "generated_at": "2026-03-25T00:00:00Z",
        "asset_class": "Stocks",
        "explanation_bullets": ["B1", "B2", "B3", "B4", "B5", "B6"],
        "tone": "neutral",
        "official_links": ["https://groww.in/pricing/stocks"],
        "last_checked": "2026-03-24",
        "provider_used": "gemini",
    }


# ── Test 1: Health Check ─────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ── Test 2: POST /api/pulse (Mocked) ─────────────────────────

@pytest.mark.asyncio
async def test_pulse_endpoint_success(mock_reviews, mock_pulse_output):
    with patch("backend.phase5.routes.ReviewScraper") as MockScraper, \
         patch("backend.phase5.routes.ReviewPulsePipeline") as MockPipeline:
        
        instance = MockScraper.return_value
        instance.scrape = AsyncMock(return_value=mock_reviews)
        
        MockPipeline.return_value.run.return_value = mock_pulse_output

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/pulse", json={
                "weeks": 4, "max_reviews": 50, "star_range_min": 1, "star_range_max": 5
            })
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "success"
            assert body["data"]["top_3_themes"] == ["Technical Issues", "High Charges", "Poor Support"]
            assert body["latency_ms"] >= 0


# ── Test 3: POST /api/pulse with No Matching Reviews ─────────

@pytest.mark.asyncio
async def test_pulse_no_reviews():
    with patch("backend.phase5.routes.ReviewScraper") as MockScraper:
        instance = MockScraper.return_value
        instance.scrape = AsyncMock(return_value=[])

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/pulse", json={
                "weeks": 1, "max_reviews": 10, "star_range_min": 5, "star_range_max": 5
            })
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "error"
            assert "No reviews" in body["error"]


# ── Test 4: POST /api/pulse Validation (Invalid Params) ──────

@pytest.mark.asyncio
async def test_pulse_invalid_params():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/pulse", json={
            "weeks": 99, "max_reviews": 5, "star_range_min": 0, "star_range_max": 10
        })
        assert resp.status_code == 422  # Pydantic validation error


# ── Test 5: POST /api/explainer (Mocked) ─────────────────────

@pytest.mark.asyncio
async def test_explainer_endpoint_success(mock_explainer_output):
    with patch("backend.phase5.routes.FeeExplainerPipeline") as MockPipeline:
        MockPipeline.return_value.run.return_value = mock_explainer_output

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/explainer", json={"asset_class": "Stocks"})
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "success"
            assert len(body["data"]["explanation_bullets"]) == 6


# ── Test 6: POST /api/explainer Invalid Asset ────────────────

@pytest.mark.asyncio
async def test_explainer_invalid_asset():
    with patch("backend.phase5.routes.FeeExplainerPipeline") as MockPipeline:
        MockPipeline.return_value.run.side_effect = ValueError("Unsupported asset class: Crypto")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/explainer", json={"asset_class": "Crypto"})
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "error"
            assert "Crypto" in body["error"]


# ── Test 7: POST /api/dispatch — All Gates OFF ───────────────

@pytest.mark.asyncio
async def test_dispatch_all_gates_off():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/dispatch", json={
            "content_type": "pulse",
            "content": {"some": "data"},
            "approvals": {"append_to_doc": False, "create_draft": False, "auto_send": False},
            "recipients": []
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["results"]["doc"]["status"] == "skipped"
        assert body["results"]["draft"]["status"] == "skipped"
        assert body["results"]["send"]["status"] == "skipped"


# ── Test 8: POST /api/dispatch — Auto-Send Without Draft ─────

@pytest.mark.asyncio
async def test_dispatch_send_without_draft():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/dispatch", json={
            "content_type": "pulse",
            "content": {"key": "value"},
            "approvals": {"append_to_doc": False, "create_draft": False, "auto_send": True},
            "recipients": ["test@example.com"]
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["results"]["send"]["status"] == "error"
        assert "Cannot auto-send without creating a draft first" in body["results"]["send"]["error"]


# ── Test 9: Swagger Docs Loads ───────────────────────────────

@pytest.mark.asyncio
async def test_swagger_docs_loads():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/docs")
        assert resp.status_code == 200


# ── Test 10: UI Filter Logic ────────────────────────────────

def test_ui_filter_star_range(mock_reviews):
    from backend.phase5.routes import _apply_ui_filters
    req = PulseRequest(weeks=8, max_reviews=200, star_range_min=4, star_range_max=5)
    filtered = _apply_ui_filters(mock_reviews, req)
    for r in filtered:
        assert r["score"] >= 4


def test_ui_filter_max_reviews(mock_reviews):
    from backend.phase5.routes import _apply_ui_filters
    req = PulseRequest(weeks=8, max_reviews=10, star_range_min=1, star_range_max=5)
    filtered = _apply_ui_filters(mock_reviews, req)
    assert len(filtered) <= 10
