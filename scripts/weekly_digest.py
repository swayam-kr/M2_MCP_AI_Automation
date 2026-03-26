"""
Weekly Digest Automation Script
================================
Called by GitHub Actions cron. Performs the full pipeline:
1. Scrape the 100 worst reviews from the past week
2. Generate the Weekly Pulse via LLM
3. Append the analysis to Google Docs
4. Create a Gmail draft of the results

Usage:
    python -m scripts.weekly_digest
"""

import os
import sys
import json
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("weekly_digest")


def main():
    logger.info("=== Groww Weekly Digest — Automated Run ===")
    logger.info(f"Timestamp: {datetime.utcnow().isoformat()}Z")

    # 1. Import pipeline components
    from backend.phase1.scraper_reviews import ReviewScraper
    from backend.phase3.pipeline_reviews import ReviewPulsePipeline
    from backend.phase7.mcp_dispatcher import MCPDispatcher
    from backend.utils import format_pulse_for_dispatch, format_explainer_for_dispatch
    from backend.config import get_setting

    # 2. Scrape reviews (100 worst from past week)
    logger.info("Step 1: Scraping 100 worst reviews from the past week...")
    scraper = ReviewScraper()
    reviews = scraper.scrape_and_filter(
        weeks=1,
        star_range_min=1,
        star_range_max=3,
        max_reviews=100
    )
    logger.info(f"  Found {len(reviews)} reviews matching filters.")

    if not reviews:
        logger.warning("No reviews found. Skipping analysis.")
        return

    # 3. Generate Weekly Pulse
    logger.info("Step 2: Generating Weekly Pulse via LLM...")
    pipeline = ReviewPulsePipeline()
    pulse = pipeline.run(
        reviews_data=reviews,
        output_file="data/weekly_pulse.json"
    )
    logger.info(f"  Pulse generated with {len(pulse.get('themes', []))} themes.")

    # 4. Format for dispatch
    logger.info("Step 3: Formatting for dispatch...")
    pulse_text = format_pulse_for_dispatch(pulse)

    # 5. Append to Google Doc
    logger.info("Step 4: Appending to Google Doc...")
    dispatcher = MCPDispatcher()
    
    period = pulse.get("period", "Current Week")
    
    content = {
        "pulse": pulse,
        "explainer": None
    }
    
    try:
        doc_result = dispatcher.dispatch(
            content=content,
            content_type="combined",
            approvals={"append_to_doc": True, "create_draft": True},
            recipients=[]
        )
        logger.info(f"  Doc: {doc_result.get('results', {}).get('doc', {}).get('status', 'unknown')}")
        logger.info(f"  Draft: {doc_result.get('results', {}).get('draft', {}).get('status', 'unknown')}")
    except Exception as e:
        logger.error(f"  Dispatch failed: {e}")

    logger.info("=== Weekly Digest Complete ===")


if __name__ == "__main__":
    main()
