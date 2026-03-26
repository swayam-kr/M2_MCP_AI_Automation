import pytest
import os
from pathlib import Path

@pytest.fixture
def sample_config():
    """Returns a minimal config dict for testing."""
    return {
        "app": {"name": "Test", "version": "1.0", "log_level": "DEBUG"},
        "part_a": {
            "app_id": "com.nextbillion.groww",
            "max_weeks": 8, "default_weeks": 4,
            "max_reviews": 200, "default_max_reviews": 100,
            "star_range_min": 1, "star_range_max": 5,
            "min_word_count": 10, "language": "en",
            "max_themes": 5, "top_themes_count": 3,
            "quotes_count": 3, "summary_max_words": 250,
            "action_ideas_count": 3,
        },
        "part_b": {
            "asset_classes": ["Stocks", "F&O", "Mutual Funds"],
            "max_bullets": 6, "official_links_count": 2,
        },
        "llm": {
            "groq": {"model": "llama3-70b-8192", "max_tokens": 2048,
                     "temperature": 0.3, "timeout_seconds": 30,
                     "context_window": 8192},
            "gemini": {"model": "gemini-2.0-flash", "max_tokens": 2048,
                       "temperature": 0.3, "timeout_seconds": 60,
                       "context_window": 32768},
            "routing": {"max_retries": 3, "backoff_base_seconds": 2,
                        "token_budget_ratio": 0.67},
        },
        "scraping": {
            "cache": {"reviews_ttl_hours": 24, "fee_kb_ttl_hours": 168},
        },
    }

@pytest.fixture
def sample_reviews():
    """Returns a list of sample review dicts for testing."""
    return [
        {"id": "r1", "content": "The app crashes every time I try to make a payment through UPI",
         "score": 1, "date": "2026-03-20", "thumbs_up": 42, "word_count": 14},
        {"id": "r2", "content": "Portfolio loading takes forever and the charts are very slow to render",
         "score": 2, "date": "2026-03-19", "thumbs_up": 28, "word_count": 13},
        {"id": "r3", "content": "Great app for mutual fund investments but needs better stock analysis features",
         "score": 4, "date": "2026-03-18", "thumbs_up": 15, "word_count": 12},
    ]

@pytest.fixture
def sample_fee_kb():
    """Returns a sample fee knowledge base dict for testing."""
    return {
        "last_scraped": "2026-03-24T00:00:00Z",
        "source": "https://groww.in/pricing",
        "asset_classes": {
            "Stocks": {
                "fees": [
                    {"name": "Brokerage", "value": "₹20 per order or 0.05%", "category": "trading"},
                    {"name": "STT", "value": "0.025% on sell side", "category": "regulatory"},
                ],
                "official_links": ["https://groww.in/pricing", "https://support.groww.in/charges"],
                "notes": "Zero brokerage on delivery trades"
            }
        }
    }
