"""
Phase 8: End-to-End Integration Tests
======================================
Covers the full test matrix from architecture.md (T13-T17).
All external services (LLM, MCP) are mocked.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport

from backend.phase5.main import app
from backend.mcp_dispatcher import MCPDispatcher


# ── Fixtures ─────────────────────────────────────────────────

@pytest.fixture
def sample_pulse_data():
    """Complete weekly pulse JSON matching schema."""
    return {
        "generated_at": "2026-03-25T10:00:00Z",
        "provider_used": "groq",
        "period": "2026-02-25 to 2026-03-25",
        "total_reviews_analyzed": 50,
        "themes": [
            {"name": "App Crashes", "review_count": 20, "sentiment": "negative", "rank": 1},
            {"name": "Slow Loading", "review_count": 15, "sentiment": "negative", "rank": 2},
            {"name": "Great UX", "review_count": 10, "sentiment": "positive", "rank": 3}
        ],
        "top_3_themes": ["App Crashes", "Slow Loading", "Great UX"],
        "quotes": [
            {"text": "App keeps crashing on payment page.", "star_rating": 1, "date": "2026-03-20"},
            {"text": "Takes forever to load my portfolio.", "star_rating": 2, "date": "2026-03-18"},
            {"text": "Love the new mutual fund section.", "star_rating": 5, "date": "2026-03-15"}
        ],
        "summary": "Analysis of 50 reviews reveals app crashes and slow loading as dominant pain points.",
        "action_ideas": ["Fix payment crash", "Optimize portfolio loading", "Expand MF features"]
    }


@pytest.fixture
def sample_explainer_data():
    """Complete fee explainer JSON matching schema."""
    return {
        "generated_at": "2026-03-25T10:00:00Z",
        "provider_used": "gemini",
        "asset_class": "Stocks",
        "explanation_bullets": [
            "Groww charges a flat ₹20 per executed order.",
            "STT of 0.025% is levied on the sell side.",
            "Exchange charges vary by exchange."
        ],
        "official_links": ["https://groww.in/pricing/stocks"],
        "last_checked": "2026-03-25",
        "tone": "neutral"
    }


# ── T13: All 3 FastAPI Endpoints Return Valid JSON ───────────

@pytest.mark.asyncio
async def test_t13_pulse_endpoint_returns_valid_json(sample_pulse_data):
    """T13a: POST /api/pulse returns valid JSON response."""
    with patch("backend.phase5.routes.ReviewScraper") as MockScraper, \
         patch("backend.phase5.routes.ReviewPulsePipeline") as MockPipeline:
        
        mock_scraper = MagicMock()
        mock_scraper.scrape = AsyncMock(return_value=[
            {"content": "Test review", "score": 3, "date": "2026-03-20T00:00:00Z"}
        ])
        MockScraper.return_value = mock_scraper
        MockPipeline.return_value.run.return_value = sample_pulse_data

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/pulse", json={
                "weeks": 4, "max_reviews": 100, "star_range_min": 1, "star_range_max": 5
            })
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "success"
            assert "data" in body
            assert body["data"]["total_reviews_analyzed"] == 50


@pytest.mark.asyncio
async def test_t13_explainer_endpoint_returns_valid_json(sample_explainer_data):
    """T13b: POST /api/explainer returns valid JSON response."""
    with patch("backend.phase5.routes.FeeExplainerPipeline") as MockPipeline:
        MockPipeline.return_value.run.return_value = sample_explainer_data

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/explainer", json={"asset_class": "Stocks"})
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "success"
            assert body["data"]["asset_class"] == "Stocks"


@pytest.mark.asyncio
async def test_t13_dispatch_endpoint_returns_valid_json():
    """T13c: POST /api/dispatch returns valid JSON response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/dispatch", json={
            "content_type": "pulse",
            "content": {"summary": "test"},
            "approvals": {"append_to_doc": False, "create_draft": False, "auto_send": False},
            "recipients": []
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert "results" in body


# ── T14: Reviews → LLM → Pulse Integration ──────────────────

@pytest.mark.asyncio
async def test_t14_reviews_to_pulse_integration(sample_pulse_data):
    """T14: Full pipeline: scraper → filter → pipeline → JSON response."""
    mock_reviews = [
        {"content": f"Test review number {i}", "score": 2, "date": "2026-03-22T00:00:00Z"}
        for i in range(20)
    ]
    
    with patch("backend.phase5.routes.ReviewScraper") as MockScraper, \
         patch("backend.phase5.routes.ReviewPulsePipeline") as MockPipeline:
        
        mock_scraper = MagicMock()
        mock_scraper.scrape = AsyncMock(return_value=mock_reviews)
        MockScraper.return_value = mock_scraper
        MockPipeline.return_value.run.return_value = sample_pulse_data

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/pulse", json={
                "weeks": 4, "max_reviews": 50, "star_range_min": 1, "star_range_max": 3
            })
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "success"
            # Pipeline received filtered data
            MockPipeline.return_value.run.assert_called_once()


# ── T15: Fee KB → LLM → Explainer Integration ───────────────

@pytest.mark.asyncio
async def test_t15_fee_kb_to_explainer_integration(sample_explainer_data):
    """T15: Full pipeline: fee KB → LLM → explainer JSON response."""
    with patch("backend.phase5.routes.FeeExplainerPipeline") as MockPipeline:
        MockPipeline.return_value.run.return_value = sample_explainer_data

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for asset_class in ["Stocks", "F&O", "Mutual Funds"]:
                resp = await client.post("/api/explainer", json={"asset_class": asset_class})
                assert resp.status_code == 200
                body = resp.json()
                assert body["status"] == "success"


# ── T16: MCP Dispatch for All 8 Gate Combos ──────────────────

@patch('backend.mcp_dispatcher.MCPDispatcher._call_mcp_tool')
def test_t16_all_8_gate_combinations(mock_call):
    """T16: Test all 2^3 = 8 gate combinations for MCP dispatch."""
    mock_call.return_value = {"result": "mock_id"}
    
    dispatcher = MCPDispatcher()
    content = {"summary": "Test content", "generated_at": "2026-03-25"}
    recipients = ["test@test.com"]
    
    combos = [
        (False, False, False),
        (True,  False, False),
        (False, True,  False),
        (False, False, True),
        (True,  True,  False),
        (True,  False, True),
        (False, True,  True),
        (True,  True,  True),
    ]
    
    for doc_on, draft_on, send_on in combos:
        mock_call.reset_mock()
        approvals = {"append_to_doc": doc_on, "create_draft": draft_on, "auto_send": send_on}
        result = dispatcher.dispatch(content, "pulse", approvals, recipients)
        
        # Verify gate logic
        if not doc_on and not draft_on and not send_on:
            mock_call.assert_not_called()
            assert result["doc"]["status"] == "skipped"
            assert result["draft"]["status"] == "skipped"
            assert result["send"]["status"] == "skipped"
        
        if doc_on:
            assert result["doc"]["status"] == "appended"
        
        if draft_on:
            assert result["draft"]["status"] == "created"
        
        if send_on and not draft_on:
            assert result["send"]["status"] == "error"
        elif send_on and draft_on:
            assert result["send"]["status"] == "sent"


# ── T17: Full Pipeline Orchestration (Mocked Externals) ──────

@pytest.mark.asyncio
async def test_t17_full_pipeline_orchestration(sample_pulse_data):
    """T17: End-to-end: Generate pulse → Dispatch to MCP (all mocked)."""
    # Step 1: Generate pulse
    with patch("backend.phase5.routes.ReviewScraper") as MockScraper, \
         patch("backend.phase5.routes.ReviewPulsePipeline") as MockPipeline:
        
        mock_scraper = MagicMock()
        mock_scraper.scrape = AsyncMock(return_value=[
            {"content": "Good app", "score": 4, "date": "2026-03-22T00:00:00Z"}
        ])
        MockScraper.return_value = mock_scraper
        MockPipeline.return_value.run.return_value = sample_pulse_data

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            pulse_resp = await client.post("/api/pulse", json={
                "weeks": 2, "max_reviews": 50, "star_range_min": 1, "star_range_max": 5
            })
            assert pulse_resp.status_code == 200
            pulse_body = pulse_resp.json()
            assert pulse_body["status"] == "success"

    # Step 2: Dispatch the generated content
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        dispatch_resp = await client.post("/api/dispatch", json={
            "content_type": "pulse",
            "content": pulse_body["data"],
            "approvals": {"append_to_doc": False, "create_draft": False, "auto_send": False},
            "recipients": []
        })
        assert dispatch_resp.status_code == 200
        dispatch_body = dispatch_resp.json()
        assert dispatch_body["status"] == "success"
        assert dispatch_body["results"]["doc"]["status"] == "skipped"


# ── T18: Input Validation Across All Endpoints ───────────────

@pytest.mark.asyncio
async def test_t18_input_validation():
    """T18: Invalid inputs return 422 with descriptive errors."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid star range (min > 5)
        resp1 = await client.post("/api/pulse", json={
            "weeks": 4, "max_reviews": 100, "star_range_min": 6, "star_range_max": 5
        })
        assert resp1.status_code == 422

        # Invalid weeks (> 8)
        resp2 = await client.post("/api/pulse", json={
            "weeks": 20, "max_reviews": 100, "star_range_min": 1, "star_range_max": 5
        })
        assert resp2.status_code == 422

        # Missing required content_type in dispatch
        resp3 = await client.post("/api/dispatch", json={
            "content": {}, "approvals": {"append_to_doc": False, "create_draft": False, "auto_send": False}
        })
        assert resp3.status_code == 422

        # Completely empty body for dispatch (missing required fields)
        resp4 = await client.post("/api/dispatch", json={})
        assert resp4.status_code == 422
