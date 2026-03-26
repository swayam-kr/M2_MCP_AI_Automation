"""
Phase 3: Weekly Review Pulse Pipeline (Part A)
==============================================
Reads filtered reviews, uses Map-Reduce to extract themes via Groq (Multi-Key),
and generates a 1-page executive summary via Gemini 2.0 Flash.
"""

import os
import json
import logging
import datetime
from typing import List, Dict, Any

from backend.phase2.llm_router import LLMRouter, LLMResponse
from backend.config import get_setting
from backend.utils import load_json, save_json

logger = logging.getLogger("pipeline_reviews")

# ── Prompts ──────────────────────────────────────────────────

MAP_PROMPT_SYSTEM = """You are a data analyst classifying user reviews.
Extract the main themes (topics) from the provided chunk of reviews.
Return ONLY valid JSON in this exact structure:
{
  "themes": [
    {
      "name": "Short Descriptive Theme Name",
      "review_count": 5,
      "avg_rating": 2.5
    }
  ]
}
Do NOT include any extra text outside the JSON.
"""

REDUCE_PROMPT_SYSTEM = """You are an executive analyst writing a Weekly Review Pulse report.
You will be given:
1. An aggregated list of all themes found across the entire dataset with total counts.
2. A sample of raw reviews for context.

Your task is to:
1. Identify the TOP 3 themes based on frequency (review_count) and impact.
2. Select EXACTLY 3 verbatim quotes from the raw reviews that perfectly illustrate the top themes. Do NOT paraphrase.
3. Write a concise executive summary (MAX 250 words) analyzing the overall user sentiment and these top issues.
4. Suggest EXACTLY 3 actionable ideas for the product team to fix the top issues.
5. NEVER include PII (emails, phone numbers, names).

Return ONLY valid JSON matching this structure exactly:
{
  "top_3_themes": ["Theme A", "Theme B", "Theme C"],
  "quotes": [
    { "text": "Exact quote 1", "star_rating": 1, "date": "2026-03-20" },
    { "text": "Exact quote 2", "star_rating": 2, "date": "2026-03-21" },
    { "text": "Exact quote 3", "star_rating": 1, "date": "2026-03-22" }
  ],
  "summary": "Your 250-word max summary here...",
  "action_ideas": [
    "Idea 1 based on themes",
    "Idea 2 based on themes",
    "Idea 3 based on themes"
  ]
}
Include specific percentage insights in the summary (e.g., "Theme X accounted for 25% of all analyzed reviews").
"""

class ReviewPulsePipeline:
    def __init__(self):
        self.router = LLMRouter()
        self.chunk_size = get_setting("pipeline.reviews.chunk_size", 50)
        
        # We enforce limits for safety
        self.max_themes = get_setting("pipeline.reviews.max_themes", 10)
        self.quotes_count = get_setting("pipeline.reviews.quotes_count", 3)
        self.action_ideas_count = get_setting("pipeline.reviews.action_ideas_count", 3)
        self.summary_max_words = get_setting("pipeline.reviews.summary_max_words", 250)

    def run(self, input_file: str = "data/reviews_filtered.json", output_file: str = "data/weekly_pulse.json", reviews_data: List[Dict] = None) -> Dict[str, Any]:
        """Runs the full Map-Reduce pipeline."""
        logger.info("Starting Weekly Review Pulse...")
        
        # 1. Load Data
        if reviews_data is not None:
            reviews = reviews_data
        else:
            try:
                reviews = load_json(input_file)
            except FileNotFoundError:
                raise FileNotFoundError(f"Missing input file: {input_file}")
                
        if not reviews:
            raise ValueError("No reviews provided for processing.")
            
        logger.info(f"Loaded {len(reviews)} reviews.")

        # 2. Chunk Data (Map phase prep)
        chunks = self._chunk_reviews(reviews, self.chunk_size)
        logger.info(f"Split tightly into {len(chunks)} chunks of ~{self.chunk_size} reviews each.")

        # 3. Classify Batches (Map phase via Groq Dual-Key)
        logger.info("Starting parallel classification (Map Phase)...")
        # Ensure we only send the text payload to save tokens
        text_chunks = []
        for c in chunks:
            chunk_text = "\\n".join([f"[{r.get('date', '')}] Rating {r.get('score', '')}: {r.get('content', '')}" for r in c])
            text_chunks.append(chunk_text)
            
        map_responses: List[LLMResponse] = self.router.classify_batch(text_chunks, MAP_PROMPT_SYSTEM)
        
        # 4. Aggregate Themes (Reduce phase prep)
        aggregated_themes = self._aggregate_themes(map_responses)
        
        # Take top themes only to avoid context bloat in Reduce
        total_mentions = sum(t["count"] for t in aggregated_themes.values())
        sorted_themes = sorted(aggregated_themes.items(), key=lambda x: x[1]["count"], reverse=True)[:self.max_themes]
        
        themes_list = []
        for name, stats in sorted_themes:
            count = stats["count"]
            total_stars = stats["total_stars"]
            avg_rating = round(total_stars / count, 1) if count > 0 else 0
            pct = round((count / total_mentions * 100), 1) if total_mentions > 0 else 0
            themes_list.append({
                "name": name, 
                "review_count": count, 
                "percentage": pct,
                "average_rating": avg_rating
            })
        
        # 5. Generate Report (Reduce phase via Gemini 2.0 Flash)
        logger.info("Starting report generation (Reduce Phase)...")
        # We need raw reviews for the LLM to pick quotes from. We'll sample 150 of the worst reviews to ensure high signal.
        worst_reviews = sorted(reviews, key=lambda x: x.get('score', 5))[:150]
        sample_context = "\\n".join([f"[{r.get('date', '')}] Rating {r.get('score', '')}: {r.get('content', '')}" for r in worst_reviews])
        
        # To make themes even richer, we tell the LLM about the avg rating per theme
        themes_summary = [f"{t['name']} ({t['review_count']} reviews, {t['percentage']}%, avg rating {t['average_rating']})" for t in themes_list]
        reduce_prompt = json.dumps({"aggregated_themes": themes_summary}) + "\\n\\nRAW REVIEWS SAMPLE FOR QUOTES:\\n" + sample_context
        
        reduce_response = self.router.generate_one_page(reduce_prompt, REDUCE_PROMPT_SYSTEM, task_name="Weekly Pulse")
        
        # 6. Parse and Validate Output
        try:
            pulse_data = json.loads(reduce_response.content)
        except json.JSONDecodeError:
            # Try to strip markdown blocks if Gemini returned them
            clean_content = reduce_response.content.replace("```json", "").replace("```", "").strip()
            pulse_data = json.loads(clean_content)

        pulse_data = self._validate_and_fix(pulse_data, reviews)
        
        # 6.5 Calculate date range and analysis context
        dates = []
        for r in reviews:
            d = r.get("date")
            if d:
                try: dates.append(datetime.datetime.fromisoformat(d.replace("Z", "+00:00")))
                except: pass
        
        if dates:
            min_date = min(dates).strftime("%b %d")
            max_date = max(dates).strftime("%b %d")
            date_range = f"{min_date} - {max_date}"
        else:
            date_range = "Current Period"

        # Construct a detailed explanation as requested
        # We assume the reviews passed in are already filtered by stars and weeks in routes.py
        # and capped at req.max_reviews.
        analysis_explanation = (
            f"This analysis is based on {len(reviews)} reviews selected by recency "
            f"that fell within the user-specified star rating and timeframe filters."
        )

        # Attach required metadata
        final_doc = {
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "provider_used": reduce_response.provider,
            "period": date_range,
            "analysis_explanation": analysis_explanation,
            "total_reviews_analyzed": len(reviews),
            "themes": themes_list,
            **pulse_data
        }
        
        # 7. Save Output
        save_json(final_doc, output_file)
            
        logger.info(f"Weekly Pulse successfully saved to {output_file}")
        return final_doc

    # ── Internal Helpers ──────────────────────────────────────────

    def _chunk_reviews(self, reviews: List[Dict], chunk_size: int) -> List[List[Dict]]:
        return [reviews[i:i + chunk_size] for i in range(0, len(reviews), chunk_size)]

    def _aggregate_themes(self, llm_responses: List[LLMResponse]) -> Dict[str, Dict[str, Any]]:
        aggr = {}
        for r in llm_responses:
            try:
                # Handle possible markdown JSON wrappers
                content = r.content.replace("```json", "").replace("```", "").strip()
                data = json.loads(content)
                themes = data.get("themes", [])
                for t in themes:
                    name = t.get("name", "Unknown").strip()
                    count = t.get("review_count", 1)
                    # We estimate star ratings per theme by looking at the average rating of reviews provided in chunks
                    # but since the Map step doesn't know which review belongs to which theme specifically,
                    # we ask the LLM in Phase 3/4 to provide an estimated avg_rating per theme if possible.
                    # For now, we'll refine the MAP_PROMPT to include star_rating extraction.
                    avg_stars = t.get("avg_rating", 3.0) 
                    
                    if name not in aggr:
                        aggr[name] = {"count": 0, "total_stars": 0}
                    aggr[name]["count"] += count
                    aggr[name]["total_stars"] += (avg_stars * count)

            except Exception as e:
                logger.warning(f"Failed to parse theme chunk: {e}")
        return aggr

    def _validate_and_fix(self, data: Dict[str, Any], raw_reviews: List[Dict]) -> Dict[str, Any]:
        """Enforces all Architecture Section 6/7 constraints via auto-fix."""
        
        # 1. Enforce Top 3 Themes
        top_3 = data.get("top_3_themes", [])
        if len(top_3) > 3:
            data["top_3_themes"] = top_3[:3]
        elif len(top_3) < 3:
            data["top_3_themes"].extend(["Needs Analysis"] * (3 - len(top_3)))
            
        # 2. Enforce EXACTLY 3 Quotes
        quotes = data.get("quotes", [])
        if len(quotes) > self.quotes_count:
            data["quotes"] = quotes[:self.quotes_count]
        elif len(quotes) < self.quotes_count:
            # Sample additional quotes if LLM missed it
            needed = self.quotes_count - len(quotes)
            worst = sorted(raw_reviews, key=lambda x: x.get('score', 5))
            for i in range(min(needed, len(worst))):
                data["quotes"].append({
                    "text": worst[i].get('content', '...'),
                    "star_rating": worst[i].get('score', 1),
                    "date": worst[i].get('date', 'Unknown')
                })
                
        # 3. Enforce exactly 3 action ideas
        ideas = data.get("action_ideas", [])
        if len(ideas) > self.action_ideas_count:
            data["action_ideas"] = ideas[:self.action_ideas_count]
        elif len(ideas) < self.action_ideas_count:
            data["action_ideas"].extend(["Review internal systems for more ideas."] * (self.action_ideas_count - len(ideas)))
            
        # 4. Enforce Summary Word Count (<= 250)
        summary = data.get("summary", "")
        words = summary.split()
        if len(words) > self.summary_max_words:
            data["summary"] = " ".join(words[:self.summary_max_words]) + "..."
            
        # 5. PII Scrubbing (Basic regex failsafe) - hard discard already ran in Phase 1, but we do a final check.
        import re
        scrubbed_summary = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}', '[EMAIL]', data["summary"])
        scrubbed_summary = re.sub(r'\\b\\d{10}\\b', '[PHONE]', scrubbed_summary)
        data["summary"] = scrubbed_summary
        
        for q in data["quotes"]:
            q["text"] = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}', '[EMAIL]', q["text"])
            q["text"] = re.sub(r'\\b\\d{10}\\b', '[PHONE]', q["text"])
            
        return data

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    
    pipeline = ReviewPulsePipeline()
    pulse = pipeline.run("data/reviews_filtered.json", "data/weekly_pulse.json")
    print(f"\\nSUCCESS. Found {len(pulse['themes'])} top themes. Extracted {len(pulse['quotes'])} quotes.")
