import asyncio
import logging
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from backend.config import get_setting
from backend.utils import save_json, is_cache_valid, load_json

logger = logging.getLogger("scraper_fees")

class FeeScraper:
    """
    Scrapes Groww pricing pages for Stocks, F&O, and Mutual Funds.
    Processes tables and text into a structured JSON knowledge base.
    """

    def __init__(self):
        self.urls = get_setting("part_b.pricing_urls")
        self.cache_file = "data/fee_kb.json"
        self.ttl_hours = get_setting("scraping.cache.fee_kb_ttl_hours", 168) # 7 days

    async def scrape(self, force: bool = False) -> Dict[str, Any]:
        """Main entry point for fee scraping."""
        if not force and is_cache_valid(self.cache_file, self.ttl_hours):
            logger.info("Loading fee KB from cache.")
            return load_json(self.cache_file)

        logger.info("Starting fresh fee scrape...")
        kb_data = {
            "last_scraped": asyncio.get_event_loop().time(), # Placeholder for datetime
            "timestamp": "", # Will fill below
            "asset_classes": {}
        }
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # 1. Scrape Stocks
            kb_data["asset_classes"]["Stocks"] = await self._scrape_stocks(page)
            
            # 2. Scrape F&O
            kb_data["asset_classes"]["F&O"] = await self._scrape_fno(page)
            
            # 3. Scrape Mutual Funds
            kb_data["asset_classes"]["Mutual Funds"] = await self._scrape_mutual_funds(page)

            await browser.close()
            
        import datetime
        kb_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        save_json(kb_data, self.cache_file)
        return kb_data

    async def _scrape_stocks(self, page) -> Dict[str, Any]:
        url = self.urls.get("Stocks")
        logger.info(f"Scraping Stocks from {url}")
        try:
            await page.goto(url, timeout=30000)
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # Extraction logic (specific to Groww pricing page)
            # This is a sample extraction - real selectors would be more precise
            data = {
                "account_opening": "Free",
                "amc": "Free",
                "equity_brokerage": "₹20 or 0.05% per order",
                "regulatory_charges": [],
                "penalties": "Standard exchange penalties apply"
            }
            
            # Look for tables (Regulatory & Statutory Charges)
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows[1:]: # Skip header
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        data["regulatory_charges"].append({
                            "charge": cols[0].text.strip(),
                            "value": cols[1].text.strip()
                        })
            
            return data
        except Exception as e:
            logger.error(f"Stocks scrape failed: {e}")
            return self._get_mock_fees("Stocks")

    async def _scrape_fno(self, page) -> Dict[str, Any]:
        url = self.urls.get("F&O")
        logger.info(f"Scraping F&O from {url}")
        try:
            await page.goto(url, timeout=30000)
            # Wait a bit for JS tables to render
            await page.wait_for_timeout(2000)
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            data = {
                "account_opening": "Free",
                "amc": "Free",
                "fno_brokerage": "₹20 per executed order",
                "regulatory_charges": [],
                "penalties": "Standard exchange penalties apply"
            }
            
            # Find all tables and extract rows from the one containing "Regulatory" or "Statutory"
            tables = soup.find_all("table")
            for table in tables:
                table_text = table.get_text().lower()
                if "regulatory" in table_text or "statutory" in table_text or "charges" in table_text:
                    rows = table.find_all("tr")
                    for row in rows:
                        cols = row.find_all(["td", "th"])
                        if len(cols) >= 2:
                            charge_name = cols[0].text.strip()
                            charge_value = cols[1].text.strip()
                            if charge_name and charge_value:
                                data["regulatory_charges"].append({
                                    "charge": charge_name,
                                    "value": charge_value
                                })
            
            # Use mock fallback only if real scraping yielded absolutely nothing
            if not data["regulatory_charges"]:
                 return self._get_mock_fees("F&O")
            return data
        except Exception as e:
            logger.error(f"F&O scrape failed: {e}")
            return self._get_mock_fees("F&O")

    async def _scrape_mutual_funds(self, page) -> Dict[str, Any]:
        url = self.urls.get("Mutual Funds")
        logger.info(f"Scraping Mutual Funds from {url}")
        try:
            await page.goto(url, timeout=30000)
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # Mutual funds blog parsing
            data = {
                "entry_load": "Nil",
                "exit_load": "Depends on the fund (usually 1% if redeemed within 1 year)",
                "transaction_charges": "Nil",
                "expense_ratio": "0.1% to 2.5% depending on direct/regular plans",
                "details": soup.text[:500] # Grab initial text as raw context
            }
            return data
        except Exception as e:
            logger.error(f"MF scrape failed: {e}")
            return self._get_mock_fees("Mutual Funds")

    def _get_mock_fees(self, asset_class: str) -> Dict[str, Any]:
        """Mock fee data for development."""
        mocks = {
            "Stocks": {
                "account_opening": "₹0 (Free)",
                "amc": "₹0 (Free)",
                "brokerage": "₹20 or 0.05% whichever is lower",
                "regulatory_charges": [
                    {"charge": "STT", "value": "0.1% on Buy & Sell"},
                    {"charge": "Stamp Duty", "value": "0.015% on Buy"}
                ],
                "official_links": ["https://groww.in/pricing/stocks"]
            },
            "F&O": {
                "brokerage": "Fixed ₹20 per order",
                "amc": "₹0",
                "regulatory_charges": [
                    {"charge": "Exchange TXN Fee", "value": "0.053% (NSE)"}
                ],
                "official_links": ["https://groww.in/pricing/futures-and-options"]
            },
            "Mutual Funds": {
                "entry_load": "Not applicable (Nil)",
                "exit_load": "0.5% - 1.0% for equity funds (if < 1 year)",
                "expense_ratio": "Varies by fund (check Groww app for exact %)",
                "official_links": ["https://groww.in/blog/mutual-fund-fees-and-charges"]
            }
        }
        return mocks.get(asset_class, {})

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = FeeScraper()
    asyncio.run(scraper.scrape(force=True))
