"""
Tests for Phase 4: Fee Structure Explainer Pipeline
===================================================
Verifies anti-hallucination validation, asset isolation,
exact-bullet counts, and mocked end-to-end runs.
"""

import pytest
import json
from unittest.mock import patch
from backend.phase4.pipeline_fees import FeeExplainerPipeline
from backend.phase2.llm_router import LLMResponse

@pytest.fixture
def mock_fee_kb():
    return {
        "timestamp": "2026-03-24T00:00:00Z",
        "asset_classes": {
            "Stocks": {
                "charges": [{"name": "Brokerage", "value": "20"}]
            },
            "F&O": {
                "charges": [{"name": "Brokerage", "value": "20"}]
            }
        }
    }

@pytest.fixture
def pipeline():
    return FeeExplainerPipeline()

# ── Test 1: Invalid Asset Class Rejection ────────────────

def test_extract_unsupported_asset(pipeline, tmp_path, mock_fee_kb):
    """Verify that unknown assets get rejected immediately."""
    kb_path = tmp_path / "fee_kb.json"
    kb_path.write_text(json.dumps(mock_fee_kb))
    
    with pytest.raises(ValueError, match="Unsupported asset class"):
        pipeline.run("Crypto", str(kb_path))

# ── Test 2: Validation Overrides LLM Links (Anti-Hallucination)

def test_validation_overrides_links(pipeline, mock_fee_kb):
    """Ensure whatever links the LLM hallucinated, we replace with real KB links."""
    llm_mock_output = {
        "explanation_bullets": ["A", "B", "C", "D", "E"],
        "tone": "neutral"
        # LLM omitted links, or we don't care if it put them.
    }
    
    validated = pipeline._validate_and_augment(
        llm_data=llm_mock_output,
        kb_asset_data=mock_fee_kb["asset_classes"]["Stocks"],
        asset_class="Stocks",
        last_scraped="2026-03-24"
    )
    
    assert validated["official_links"] == ["https://groww.in/pricing/stocks"]
    assert validated["last_checked"] == "2026-03-24"
    assert validated["tone"] == "neutral"

# ── Test 3: Exact Bullet Counts ──────────────────────────

def test_validation_bullet_counts(pipeline, mock_fee_kb):
    """Verify bullet counts are truncated or padded to exactly self.max_bullets (6)."""
    # 1. Oversize
    llm_mock_10 = {
        "explanation_bullets": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "tone": "neutral"
    }
    v1 = pipeline._validate_and_augment(llm_mock_10, mock_fee_kb["asset_classes"]["Stocks"], "Stocks", "2026-03-24")
    assert len(v1["explanation_bullets"]) == 6
    assert v1["explanation_bullets"] == ["1", "2", "3", "4", "5", "6"]
    
    # 2. Undersize
    llm_mock_2 = {
        "explanation_bullets": ["1", "2"],
        "tone": "neutral"
    }
    v2 = pipeline._validate_and_augment(llm_mock_2, mock_fee_kb["asset_classes"]["Stocks"], "Stocks", "2026-03-24")
    assert len(v2["explanation_bullets"]) == 6
    assert "Refer to the official source link for more details." in v2["explanation_bullets"]

# ── Test 4: Promotional Tone Flagger ─────────────────────

def test_promotional_tone_flagging(pipeline, mock_fee_kb):
    """Ensure positive buzzwords trigger a tone flag."""
    llm_mock = {
        "explanation_bullets": ["The best brokerage platform!", "Amazing rates."],
        "tone": "neutral" # LLM claimed it was neutral
    }
    
    v = pipeline._validate_and_augment(llm_mock, mock_fee_kb["asset_classes"]["Stocks"], "Stocks", "x")
    assert v["tone"] == "flagged_promotional"

# ── Test 5: End-to-End Mocked ────────────────────────────

def test_end_to_end_mocked(pipeline, tmp_path, mock_fee_kb):
    """Full execution path avoiding real APIs."""
    kb_path = tmp_path / "fee_kb.json"
    kb_path.write_text(json.dumps(mock_fee_kb))
    out_path = tmp_path / "explainer.json"
    
    mock_llm = LLMResponse(
        content=json.dumps({"explanation_bullets": ["Fast", "Cheap", "Good", "Yes", "Ok", "Fine"], "tone": "neutral"}),
        provider="gemini", tokens_used=10, latency_ms=10, model="gemini-2.0"
    )
    
    with patch.object(pipeline.router, 'generate_one_page', return_value=mock_llm):
        result = pipeline.run("Stocks", input_file=str(kb_path), output_file=str(out_path))
        
        assert result["asset_class"] == "Stocks"
        assert len(result["explanation_bullets"]) == 6
        assert result["official_links"][0] == "https://groww.in/pricing/stocks"
        assert out_path.exists()
