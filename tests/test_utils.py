import sys
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from backend.utils import scrub_pii, estimate_tokens, fits_in_context

def test_scrub_email():
    assert "[REDACTED]" in scrub_pii("Email me at test@gmail.com")
    assert "test@gmail.com" not in scrub_pii("Email me at test@gmail.com")

def test_scrub_phone():
    assert "[REDACTED]" in scrub_pii("Call 9876543210 for help")
    assert "9876543210" not in scrub_pii("Call 9876543210 for help")

def test_scrub_aadhaar():
    assert "[REDACTED]" in scrub_pii("My Aadhaar is 1234 5678 9012")

def test_scrub_preserves_clean_text():
    clean = "This is a clean review with no personal info"
    assert scrub_pii(clean) == clean

def test_estimate_tokens():
    # "Hello world" = 11 chars -> ~2-3 tokens
    assert 1 <= estimate_tokens("Hello world") <= 5

def test_fits_in_context_small():
    assert fits_in_context("short text", 8192, 0.67) is True

def test_fits_in_context_large():
    # Roughly 1 token per 4 characters. Window 8192, 67% = 5488 tokens.
    # 5488 * 4 = 21952 chars. Let's make it larger.
    large_text = "word " * 10000  # 50000 chars -> ~12500 tokens
    assert fits_in_context(large_text, 8192, 0.67) is False
