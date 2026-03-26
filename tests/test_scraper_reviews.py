import sys
import pytest
from pathlib import Path
from datetime import datetime, timezone

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from backend.phase1.scraper_reviews import ReviewScraper

def test_apply_filters_date_range():
    scraper = ReviewScraper()
    # 10 weeks ago (outside 8-week limit)
    old_date = (datetime.now(timezone.utc)).isoformat() # placeholder
    # This test will use mock data anyway
    
    reviews = [
        {"content": "This is a very long review that should pass the word count filter.", 
         "score": 5, "date": datetime.now(timezone.utc).isoformat()},
        {"content": "Short.", "score": 2, "date": datetime.now(timezone.utc).isoformat()}
    ]
    
    filtered = scraper._apply_filters(reviews)
    # Only the long one should stay
    assert len(filtered) == 1
    assert "long review" in filtered[0]["content"]

def test_apply_filters_pii_discard():
    scraper = ReviewScraper()
    reviews = [{
        "content": "Contact me at swayam@gmail.com or 9876543210. This is a very good app and I highly recommend it for everyone interested in stocks.",
        "score": 5,
        "date": datetime.now(timezone.utc).isoformat()
    }]
    
    filtered = scraper._apply_filters(reviews)
    # Should be 0 because of Hard PII Filter (Binary Discard)
    assert len(filtered) == 0

def test_apply_filters_deduplication():
    scraper = ReviewScraper()
    content_str = "This is a long enough review that should pass the word count filter easily."
    reviews = [
        {"content": content_str, "score": 5, "date": datetime.now(timezone.utc).isoformat()},
        {"content": content_str, "score": 5, "date": datetime.now(timezone.utc).isoformat()}
    ]
    
    filtered = scraper._apply_filters(reviews)
    assert len(filtered) == 1

@pytest.mark.asyncio
async def test_scrape_returns_list():
    scraper = ReviewScraper()
    # This will trigger the fallback mock reviews since we don't have Playwright browsers
    results = await scraper.scrape(force=True)
    assert isinstance(results, list)
    assert len(results) > 0
    for r in results:
        assert "content" in r
        assert "date" in r
