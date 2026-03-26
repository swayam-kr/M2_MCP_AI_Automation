"""
Phase 4: Fee Structure Explainer Pipeline (Part B)
==================================================
Reads extracted fee knowledge base (fee_kb.json), and uses the Specialized LLM Engine
(Gemini 2.0 Flash) to synthesize exactly 6 easy-to-read explanation bullets.
Employs an anti-hallucination design by strictly appending official links and 
timestamps programmatically outside the LLM context.
"""

import os
import json
import logging
import argparse
import datetime
from typing import Dict, Any, List

from backend.phase2.llm_router import LLMRouter, LLMResponse
from backend.config import get_setting

logger = logging.getLogger("pipeline_fees")

EXPLAINER_PROMPT_SYSTEM = """You are a financial fee explanation assistant for Groww.
Your ONLY job is to explain the provided fee structure to a beginner investor.

STRICT INSTRUCTIONS:
1. Use ONLY the fee data provided below. Do NOT add any fees or charges not present in the data.
2. If you are unsure about a fee, do NOT include it.
3. Write EXACTLY {max_bullets} bullet points explaining the most important charges.
4. Keep the tone completely neutral and objective. Do NOT use marketing or promotional language.
5. Each bullet should be one clear sentence.

Return ONLY valid JSON matching this exact structure:
{{
  "explanation_bullets": [
    "Bullet 1",
    "Bullet 2",
    "Bullet 3",
    "Bullet 4",
    "Bullet 5",
    "Bullet 6"
  ],
  "tone": "neutral"
}}
Do NOT include the word ```json or any markdown formatting.
"""

class FeeExplainerPipeline:
    def __init__(self):
        self.router = LLMRouter()
        self.valid_assets = get_setting("part_b.asset_classes", ["Stocks", "F&O", "Mutual Funds"])
        self.max_bullets = get_setting("part_b.max_bullets", 6)

    def run(self, asset_class: str, input_file: str = "data/fee_kb.json", output_file: str = "data/fee_explainer.json") -> Dict[str, Any]:
        """Runs the Anti-Hallucination Fee Explainer pipeline."""
        logger.info(f"Starting Fee Explainer for asset: '{asset_class}'...")
        
        # 1. Validation
        if asset_class not in self.valid_assets:
            raise ValueError(f"Unsupported asset class: {asset_class}. Must be one of {self.valid_assets}")

        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Missing input KB file: {input_file}")
            
        with open(input_file, 'r', encoding='utf-8') as f:
            kb = json.load(f)
            
        # 2. Extract specific asset class data
        asset_data = kb.get("asset_classes", {}).get(asset_class)
        if not asset_data:
            raise ValueError(f"No KB data found in {input_file} for asset class: {asset_class}")
            
        logger.info(f"Loaded fee records for {asset_class}.")

        # 3. Build Safe Prompt
        # Inject the raw stringified data into the user prompt
        raw_context = json.dumps(asset_data, indent=2)
        user_prompt = f"ASSET CLASS: {asset_class}\\n\\nRAW FEE DATA:\\n{raw_context}"
        
        system_prompt = EXPLAINER_PROMPT_SYSTEM.format(max_bullets=self.max_bullets)

        # 4. Generate via Gemini (High Reasoning)
        logger.info("Calling Specialized Engine (Gemini) to synthesize bullets...")
        resp = self.router.generate_one_page(user_prompt, system_prompt, task_name=f"Fee Explainer - {asset_class}")
        
        # Parse output
        try:
            content = resp.content.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
                
            llm_output = json.loads(content)
        except Exception as e:
            logger.error(f"Failed to parse LLM JSON: {e}\\nRaw Content: {resp.content}")
            raise

        # 5. Validation and Failsafe Appends
        validated_data = self._validate_and_augment(llm_output, asset_data, asset_class, kb.get("timestamp"))
        validated_data["provider_used"] = resp.provider

        # 6. Save
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(validated_data, f, indent=2)
            
        logger.info(f"Fee Explainer saved to {output_file}")
        return validated_data

    # ── Internal Helpers ──────────────────────────────────────────

    def _validate_and_augment(self, llm_data: Dict[str, Any], kb_asset_data: Dict[str, Any], asset_class: str, last_scraped: str) -> Dict[str, Any]:
        """
        Anti-Hallucination rules:
        - Ensures exactly max_bullets
        - Overrides LLM-generated URLs with the actual Knowledge Base URLs
        - Submits actual last_scraped date
        """
        bullets = llm_data.get("explanation_bullets", [])
        
        # Enforce exact bullet count truncation
        if len(bullets) > self.max_bullets:
            bullets = bullets[:self.max_bullets]
            
        # Optional padding if LLM failed to write enough
        while len(bullets) < self.max_bullets:
            bullets.append(f"Refer to the official source link for more details.")

        # Flag promotional language (Basic heuristic)
        tone = llm_data.get("tone", "neutral")
        promotional_words = ["best", "fantastic", "amazing", "revolutionary", "lowest", "unbeatable"]
        for word in promotional_words:
            if word in str(bullets).lower():
                tone = "flagged_promotional"
                break

        return {
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "asset_class": asset_class,
            "explanation_bullets": bullets,
            "tone": tone,
            # CRITICAL: We DO NOT use any links the LLM might have hallucinated. Let's pull from config.
            "official_links": [get_setting("part_b.pricing_urls", {}).get(asset_class, "https://groww.in/pricing")],
            "last_checked": last_scraped or "Unknown"
        }

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    
    parser = argparse.ArgumentParser(description="Generate Fee Explainer JSON")
    parser.add_argument("--asset", type=str, default="Stocks", help="Asset Class (Stocks, F&O, Mutual Funds)")
    args = parser.parse_args()
    
    pipeline = FeeExplainerPipeline()
    pipeline.run(args.asset)
