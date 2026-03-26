"""
Tests for Phase 3: Weekly Review Pulse Pipeline
================================================
Verifies chunking logic, map-reduce theme aggregation, post-LLM constraint
validation (truncation, padding), and mocked end-to-end runs.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from backend.phase3.pipeline_reviews import ReviewPulsePipeline
from backend.phase2.llm_router import LLMResponse

@pytest.fixture
def dummy_reviews():
    """Generates 120 dummy reviews for testing chunking."""
    return [{"content": f"Review {i}", "score": 1, "date": "2026-03-24"} for i in range(120)]

@pytest.fixture
def pipeline():
    return ReviewPulsePipeline()

# ── Test 1: Chunking Logic ─────────────────────────────────

def test_chunk_reviews(pipeline, dummy_reviews):
    """Verify that a list is split correctly into config chunks."""
    pipeline.chunk_size = 50
    chunks = pipeline._chunk_reviews(dummy_reviews, 50)
    
    assert len(chunks) == 3   # 50, 50, 20
    assert len(chunks[0]) == 50
    assert len(chunks[1]) == 50
    assert len(chunks[2]) == 20

# ── Test 2: Theme Aggregation ───────────────────────────────

def test_aggregate_themes(pipeline):
    """Verify Map-Reduce properly merges theme counts across chunks."""
    # Mock some responses from LLM classify_batch
    resp1 = LLMResponse(
        content=json.dumps({"themes": [
            {"name": "App Crash", "review_count": 5},
            {"name": "Slow UI", "review_count": 2}
        ]}),
        provider="groq", tokens_used=100, latency_ms=100, model="llama3"
    )
    resp2 = LLMResponse(
        content=json.dumps({"themes": [
            {"name": "App Crash", "review_count": 3},
            {"name": "Login Issue", "review_count": 4}
        ]}),
        provider="groq", tokens_used=100, latency_ms=100, model="llama3"
    )
    
    aggr = pipeline._aggregate_themes([resp1, resp2])
    
    assert aggr["App Crash"] == 8
    assert aggr["Slow UI"] == 2
    assert aggr["Login Issue"] == 4

# ── Test 3: Constraint Validation (Over-limits) ─────────────

def test_validation_auto_fix_oversize(pipeline, dummy_reviews):
    """Verify that if LLM returns >3 items or long summaries, they are truncated."""
    raw_output = {
        "top_3_themes": ["A", "B", "C", "D", "E"],
        "quotes": [
            {"text": "1", "star_rating": 1, "date": "x"},
            {"text": "2", "star_rating": 1, "date": "x"},
            {"text": "3", "star_rating": 1, "date": "x"},
            {"text": "4", "star_rating": 1, "date": "x"}
        ],
        "summary": "word " * 300, # 300 words
        "action_ideas": ["I1", "I2", "I3", "I4"]
    }
    
    fixed = pipeline._validate_and_fix(raw_output, dummy_reviews)
    
    assert len(fixed["top_3_themes"]) == 3
    assert len(fixed["quotes"]) == 3
    assert len(fixed["action_ideas"]) == 3
    assert len(fixed["summary"].split()) <= 251 # 250 words + "..."

# ── Test 4: Constraint Validation (Under-limits) ────────────

def test_validation_auto_fix_undersize(pipeline, dummy_reviews):
    """Verify that if LLM returns <3 items, it pads from raw data correctly."""
    raw_output = {
        "top_3_themes": ["A"],
        "quotes": [
            {"text": "1", "star_rating": 1, "date": "x"}
        ],
        "summary": "Short",
        "action_ideas": ["Idea 1"]
    }
    
    fixed = pipeline._validate_and_fix(raw_output, dummy_reviews)
    
    assert len(fixed["top_3_themes"]) == 3
    assert fixed["top_3_themes"][1] == "Needs Analysis"
    
    assert len(fixed["quotes"]) == 3
    assert fixed["quotes"][1]["text"] == "Review 0" # Sampled from worst dummy reviews
    
    assert len(fixed["action_ideas"]) == 3
    assert "Review internal systems for more ideas." == fixed["action_ideas"][1]

# ── Test 5: End-to-End Mocked Run ──────────────────────────

def test_pipeline_run_mocked(pipeline, tmp_path, dummy_reviews):
    """Smoke test for the whole pipeline avoiding real APIs."""
    input_file = tmp_path / "reviews.json"
    output_file = tmp_path / "pulse.json"
    
    with open(input_file, 'w') as f:
        json.dump(dummy_reviews, f)
        
    mock_map = LLMResponse(
        content=json.dumps({"themes": [{"name": "Mock Theme", "review_count": 10}]}),
        provider="groq", tokens_used=50, latency_ms=10, model="llama3"
    )
    mock_reduce = LLMResponse(
        content=json.dumps({
            "top_3_themes": ["Mock Theme"],
            "quotes": [{"text": "Ouch", "star_rating": 1, "date": "x"}],
            "summary": "The app is okay.",
            "action_ideas": ["Fix things"]
        }),
        provider="gemini", tokens_used=200, latency_ms=20, model="gemini-2.0"
    )
    
    with patch.object(pipeline.router, 'classify_batch', return_value=[mock_map]*3):
        with patch.object(pipeline.router, 'generate_one_page', return_value=mock_reduce):
            result = pipeline.run(str(input_file), str(output_file))
            
            assert "themes" in result
            assert result["themes"][0]["name"] == "Mock Theme"
            assert result["themes"][0]["review_count"] == 30 # Aggregated from 3 chunks
            assert len(result["top_3_themes"]) == 3 # Auto-padded
            
            # File should exist
            assert output_file.exists()
