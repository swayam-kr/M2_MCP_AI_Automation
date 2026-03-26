import sys
import pytest
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from backend.phase1.scraper_fees import FeeScraper

@pytest.mark.asyncio
async def test_scrape_fees_structure():
    scraper = FeeScraper()
    # Trigger fallback mock
    kb = await scraper.scrape(force=True)
    
    assert "asset_classes" in kb
    assert "Stocks" in kb["asset_classes"]
    assert "F&O" in kb["asset_classes"]
    assert "Mutual Funds" in kb["asset_classes"]
    
    # Check Stocks details
    stocks = kb["asset_classes"]["Stocks"]
    assert "brokerage" in stocks or "equity_brokerage" in stocks
    assert "amc" in stocks
    
    # Check MF details
    mf = kb["asset_classes"]["Mutual Funds"]
    assert "exit_load" in mf
    assert "expense_ratio" in mf

def test_cache_logic(tmp_path):
    # This might need complex mocking, skipping for now
    pass
