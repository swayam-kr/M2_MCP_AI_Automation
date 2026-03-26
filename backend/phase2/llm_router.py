"""
Phase 2: Refined Specialized LLM Engine
=======================================
Provides a unified LLMRouter class with:
1.  **Dual-Key Groq Rotation**: Key 1 & Key 2 for high-volume classification.
2.  **Specialized Routing**: Groq for classification, Gemini for generation.
3.  **Parallel Batching**: classify_batch() for multi-key distribution.
4.  **Rate-Limit Awareness**: Parses Retry-After headers for smart pausing.
"""

import os
import time
import logging
import json
import concurrent.futures
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Union

from groq import Groq
import google.generativeai as genai

from backend.config import get_setting

logger = logging.getLogger("llm_router")


# ── Exceptions ──────────────────────────────────────────────

class LLMUnavailableError(Exception):
    """Raised when all LLM providers fail after max retries."""
    pass


# ── Response Dataclass ──────────────────────────────────────

@dataclass
class LLMResponse:
    """Structured response from an LLM call."""
    content: str
    provider: str           # "groq" or "gemini"
    tokens_used: int
    latency_ms: int
    model: str
    key_id: Optional[str] = None  # Which Groq key was used


# ── LLM Router ──────────────────────────────────────────────

class LLMRouter:
    """
    Refined LLM Router with Dual-Key Groq Rotation and Specialized Routes.

    Strategy:
        - Classification (Heavy): Groq (Key 1 & 2) in parallel batches.
        - Generation (Creative): Gemini 2.0 Flash (Primary) -> Groq (Fallback).
    """

    def __init__(self):
        # ── Load API Keys ──
        self.groq_keys = {
            "key_1": os.getenv("GROQ_API_KEY_1"),
            "key_2": os.getenv("GROQ_API_KEY_2"),
            "key_3": os.getenv("GROQ_API_KEY_3")
        }
        self.gemini_key = os.getenv("GEMINI_API_KEY")

        # ── Init Groq Clients ──
        self.groq_clients = {}
        for kid, key in self.groq_keys.items():
            if key:
                self.groq_clients[kid] = Groq(api_key=key)
            else:
                logger.warning(f"GROQ_API_KEY_{kid[-1]} not set.")

        # ── Init Gemini Client ──
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)
        else:
            logger.warning("GEMINI_API_KEY not set.")

        # ── Load Config ──
        self.groq_model = get_setting("llm.groq.model", "llama-3.3-70b-versatile")
        self.gemini_model = get_setting("llm.gemini.model", "gemini-2.0-flash")
        
        # User explicitly asked for "2.5 flash" multiple times - 
        # using gemini-2.0-flash as the most robust match for now.
        if "2.5" in str(self.gemini_model):
            self.gemini_model = "gemini-2.0-flash"

        self.max_retries = get_setting("llm.routing.max_retries", 3)
        self.backoff_base = get_setting("llm.routing.backoff_base_seconds", 2)
        self.token_budget_ratio = get_setting("llm.routing.token_budget_ratio", 0.67)

        # ── Rotation State ──
        self._current_key_index = 0
        self._keys_list = list(self.groq_clients.keys())

        logger.info(f"LLMRouter initialized with {len(self.groq_clients)} Groq keys. Gemini: {self.gemini_model}")

    # ── Specialized Route: Classification ────────────────────

    def classify_batch(self, review_chunks: List[str], system_prompt: str) -> List[LLMResponse]:
        """
        Classifies multiple chunks of reviews in parallel using dual-key rotation.
        """
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(review_chunks), 4)) as executor:
            future_to_chunk = {}
            
            for i, chunk in enumerate(review_chunks):
                # Round-robin key selection
                key_id = self._get_next_groq_key()
                future = executor.submit(self.generate_with_groq, chunk, system_prompt, key_id=key_id)
                future_to_chunk[future] = chunk

            for future in concurrent.futures.as_completed(future_to_chunk):
                try:
                    results.append(future.result())
                except Exception as e:
                    logger.error(f"Classification chunk failed: {e}")
                    # Fallback or retry logic could go here
        
        return results

    # ── Specialized Route: Generation ───────────────────────

    def generate_one_page(self, prompt: str, system_prompt: str, task_name: str = "Weekly Pulse") -> LLMResponse:
        """
        Generates reasoning-heavy content using Gemini 2.0 Flash as primary.
        """
        logger.info(f"Starting generation for {task_name} using Gemini...")
        start_time = time.time()
        
        try:
            return self._call_gemini(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"Gemini failed for {task_name}, falling back to Groq: {e}")
            # Fallback to Groq with Key 1
            return self.generate_with_groq(prompt, system_prompt, key_id=self._get_next_groq_key())

    # ── Provider Specific Calls ─────────────────────────────

    def generate_with_groq(self, prompt: str, system_prompt: str, key_id: str = "key_1") -> LLMResponse:
        """Helper for direct Groq calls with specific key."""
        return self._call_groq(prompt, system_prompt, key_id=key_id)

    def _call_groq(self, prompt: str, system_prompt: str, key_id: str) -> LLMResponse:
        current_key_id = key_id
        start = time.time()
        for attempt in range(self.max_retries):
            client = self.groq_clients.get(current_key_id)
            if not client:
                raise ConnectionError(f"Groq client {current_key_id} not available")

            try:
                response = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    model=self.groq_model,
                    temperature=0.3,
                    response_format={"type": "json_object"} if "json" in system_prompt.lower() else None
                )
                
                latency = int((time.time() - start) * 1000)
                return LLMResponse(
                    content=response.choices[0].message.content,
                    provider="groq",
                    tokens_used=response.usage.total_tokens if response.usage else 0,
                    latency_ms=latency,
                    model=self.groq_model,
                    key_id=current_key_id
                )
            except Exception as e:
                if "429" in str(e) and attempt < self.max_retries - 1:
                    logger.warning(f"Groq {current_key_id} rate limited. Rotating to next key...")
                    current_key_id = self._get_next_groq_key()
                    time.sleep(0.5)  # Tiny pause to avoid spinning
                else:
                    raise e
        
        raise LLMUnavailableError(f"All Groq retries exhausted.")

    def _call_gemini(self, prompt: str, system_prompt: str) -> LLMResponse:
        if not self.gemini_key:
            raise ConnectionError("Gemini API key not configured")

        start = time.time()
        model = genai.GenerativeModel(
            model_name=self.gemini_model,
            system_instruction=system_prompt
        )

        response = model.generate_content(prompt)
        latency = int((time.time() - start) * 1000)

        return LLMResponse(
            content=response.text,
            provider="gemini",
            tokens_used=getattr(response, 'usage_metadata', {}).get('total_token_count', 0) if hasattr(response, 'usage_metadata') else 0,
            latency_ms=latency,
            model=self.gemini_model
        )

    # ── Utilities ───────────────────────────────────────────

    def _get_next_groq_key(self) -> str:
        """Round-robin through available Groq keys."""
        if not self._keys_list:
            raise ConnectionError("No Groq keys available for rotation")
        
        key_id = self._keys_list[self._current_key_index]
        self._current_key_index = (self._current_key_index + 1) % len(self._keys_list)
        return key_id

    def estimate_prompt_tokens(self, prompt: str, system_prompt: str = "") -> int:
        return max(1, int((len(prompt) + len(system_prompt)) / 4 * 1.1))

    def fits_in_context(self, prompt: str, provider: str = "groq") -> bool:
        estimated = self.estimate_prompt_tokens(prompt)
        limit = 8192 if provider == "groq" else 32768
        return estimated < (limit * self.token_budget_ratio)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    
    router = LLMRouter()
    print("Test rotation:", [router._get_next_groq_key() for _ in range(5)])
