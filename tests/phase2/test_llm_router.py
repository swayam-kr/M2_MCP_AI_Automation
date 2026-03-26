"""
Tests for Refined Specialized LLM Engine
=========================================
Verifies:
1.  Dual-Key Groq Rotation (Key 1 & Key 2).
2.  Parallel Batch Classification.
3.  Specialized Routing (Gemini for Pulse/Fee).
4.  Fallback Logic (Gemini -> Groq).
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from backend.phase2.llm_router import LLMRouter, LLMResponse, LLMUnavailableError

@pytest.fixture
def router():
    # Mock OS environment for keys
    with patch.dict('os.environ', {
        'GROQ_API_KEY_1': 'gsk_mock_1',
        'GROQ_API_KEY_2': 'gsk_mock_2',
        'GEMINI_API_KEY': 'mock_gemini'
    }):
        return LLMRouter()

# ── Test 1: Dual-Key Rotation ──────────────────────────────

def test_groq_key_rotation(router):
    """Verify that Groq keys alternate in round-robin fashion."""
    k1 = router._get_next_groq_key()
    k2 = router._get_next_groq_key()
    k3 = router._get_next_groq_key()
    
    assert k1 == "key_1"
    assert k2 == "key_2"
    assert k3 == "key_1"

# ── Test 2: Parallel Batch Classification ──────────────────

def test_classify_batch_parallelism(router):
    """Verify that classify_batch uses rotation and completes all chunks."""
    chunks = ["Review 1", "Review 2", "Review 3"]
    mock_resp = LLMResponse("OK", "groq", 10, 100, "llama3", key_id="mock")
    
    with patch.object(router, 'generate_with_groq', return_value=mock_resp) as mock_gen:
        results = router.classify_batch(chunks, "Classify this")
        
        assert len(results) == 3
        assert mock_gen.call_count == 3
        # Verify rotation was called
        calls = [call.kwargs.get('key_id') for call in mock_gen.call_args_list]
        assert "key_1" in calls
        assert "key_2" in calls

# ── Test 3: Specialized Generation Route (Gemini) ──────────

def test_generate_one_page_gemini_success(router):
    """Verify that generate_one_page defaults to Gemini."""
    mock_resp = LLMResponse("Pulse content", "gemini", 100, 500, "gemini-2.0")
    
    with patch.object(router, '_call_gemini', return_value=mock_resp) as mock_gem:
        res = router.generate_one_page("Generate report", "You are an analyst")
        assert res.provider == "gemini"
        mock_gem.assert_called_once()

# ── Test 4: Generation Fallback (Gemini -> Groq) ───────────

def test_generate_one_page_fallback(router):
    """Verify fallback to Groq if Gemini fails."""
    mock_groq_resp = LLMResponse("Pulse content from Groq", "groq", 100, 200, "llama3", key_id="key_1")
    
    with patch.object(router, '_call_gemini', side_effect=Exception("Gemini 429")):
        with patch.object(router, 'generate_with_groq', return_value=mock_groq_resp) as mock_groq:
            res = router.generate_one_page("Generate report", "You are an analyst")
            assert res.provider == "groq"
            mock_groq.assert_called_once()

# ── Test 5: Token Estimation ──────────────────────────────

def test_token_estimation(router):
    """Verify basic token estimator logic."""
    text = "Hello world" # 11 chars
    # (11/4) * 1.1 = 3.025 -> 3
    assert router.estimate_prompt_tokens(text) == 3

# ── Test 6: Fits in Context ───────────────────────────────

def test_fits_in_context(router):
    """Verify fits_in_context boundaries."""
    # Groq budget: 8192 * 0.67 = 5488 tokens -> ~21k chars
    small = "x" * 1000
    huge = "x" * 50000
    
    assert router.fits_in_context(small, provider="groq") is True
    assert router.fits_in_context(huge, provider="groq") is False
