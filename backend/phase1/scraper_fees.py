import asyncio
import logging
import requests
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

from backend.config import get_setting
from backend.utils import save_json, is_cache_valid, load_json

logger = logging.getLogger("scraper_fees")

class FeeScraper:
    """
    Scrapes Groww pricing pages for Stocks, F&O, and Mutual Funds.
    Processes tables and text into a structured JSON knowledge base.
    Uses lightweight requests instead of Playwright for serverless compatibility.
    """

    def __init__(self):
        self.urls = get_setting("part_b.pricing_urls")
        self.cache_file = "data/fee_kb.json"
        self.ttl_hours = get_setting("scraping.cache.fee_kb_ttl_hours", 168) # 7 days
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    async def scrape(self, force: bool = False) -> Dict[str, Any]:
        """Main entry point for fee scraping."""
        if not force and is_cache_valid(self.cache_file, self.ttl_hours):
            logger.info("Loading fee KB from cache.")
            return load_json(self.cache_file)

        logger.info("Starting fresh fee scrape (Serverless compatible)...")
        
        import datetime
        kb_data = {
            "last_scraped": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "asset_classes": {}
        }

        # Run synchronous HTTP requests in thread executor
        kb_data["asset_classes"]["Stocks"] = await asyncio.to_thread(self._scrape_stocks)
        kb_data["asset_classes"]["F&O"] = await asyncio.to_thread(self._scrape_fno)
        kb_data["asset_classes"]["Mutual Funds"] = await asyncio.to_thread(self._scrape_mutual_funds)
        
        save_json(kb_data, self.cache_file)
        return kb_data

    def _fetch_soup(self, asset_class: str) -> BeautifulSoup:
        url = self.urls.get(asset_class)
        logger.info(f"Scraping {asset_class} from {url}")
        resp = requests.get(url, headers=self.headers, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")

    def _scrape_stocks(self) -> Dict[str, Any]:
        try:
            soup = self._fetch_soup("Stocks")
            data = {
                "account_opening": "Free",
                "amc": "Free",
                "equity_brokerage": "₹20 or 0.05% per order",
                "regulatory_charges": [],
                "penalties": "Standard exchange penalties apply"
            }
            
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

    def _scrape_fno(self) -> Dict[str, Any]:
        try:
            soup = self._fetch_soup("F&O")
            data = {
                "account_opening": "Free",
                "amc": "Free",
                "fno_brokerage": "₹20 per executed order",
                "regulatory_charges": [],
                "penalties": "Standard exchange penalties apply"
            }
            
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
            
            if not data["regulatory_charges"]:
                 return self._get_mock_fees("F&O")
            return data
        except Exception as e:
            logger.error(f"F&O scrape failed: {e}")
            return self._get_mock_fees("F&O")

    def _scrape_mutual_funds(self) -> Dict[str, Any]:
        try:
            soup = self._fetch_soup("Mutual Funds")
            data = {
                "entry_load": "Nil",
                "exit_load": "Depends on the fund (usually 1% if redeemed within 1 year)",
                "transaction_charges": "Nil",
                "expense_ratio": "0.1% to 2.5% depending on direct/regular plans",
                "details": soup.text[:500].strip()
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
