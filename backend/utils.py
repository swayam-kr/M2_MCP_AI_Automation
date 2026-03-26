import re
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("utils")

# ── PII Scrubbing ──────────────────────────────────────────

# Regex patterns for PII detection
PII_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "phone_10_13": r"\b\d{10,13}\b",
    "aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
}


def scrub_pii(text: str) -> str:
    """
    Remove all PII patterns from text.
    Returns cleaned text.
    """
    cleaned = text
    for pattern_name, pattern in PII_PATTERNS.items():
        cleaned = re.sub(pattern, "[REDACTED]", cleaned)
    return cleaned


def has_pii(text: str) -> bool:
    """
    Check if text contains any PII patterns.

    Parameters:
        text: Input text to check

    Returns:
        True if any PII pattern is found, False otherwise.
    """
    for pattern_name, pattern in PII_PATTERNS.items():
        if re.search(pattern, text):
            return True
    return False


# ── Token Estimation ──────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """
    Rough token count estimation.
    Rule of thumb: 1 token ≈ 4 characters for English text.

    Parameters:
        text: Input text to estimate tokens for

    Returns:
        Estimated token count (integer)

    Example:
        estimate_tokens("Hello world")  -> 2
    """
    return max(1, len(text) // 4)


def fits_in_context(text: str, context_window: int, budget_ratio: float = 0.67) -> bool:
    """
    Check if text fits within the token budget.

    Parameters:
        text: Input text
        context_window: Total context window size in tokens
        budget_ratio: Fraction of context window reserved for input (default 0.67)

    Returns:
        True if estimated tokens < context_window * budget_ratio
    """
    budget = int(context_window * budget_ratio)
    estimated = estimate_tokens(text)
    logger.debug(f"Token check: {estimated} estimated vs {budget} budget")
    return estimated < budget


# ── Cache TTL Check ───────────────────────────────────────

def is_cache_valid(file_path: str, ttl_hours: int) -> bool:
    """
    Check if a cached JSON file is still within its TTL.

    Parameters:
        file_path: Path to the cached JSON file
        ttl_hours: Time-to-live in hours

    Returns:
        True if file exists AND was modified within ttl_hours.
        False if file doesn't exist or is older than ttl_hours.

    Example:
        is_cache_valid("data/reviews_raw.json", 24)  -> True/False
    """
    path = Path(file_path)
    if not path.exists():
        return False

    modified_time = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - modified_time).total_seconds() / 3600
    is_valid = age_hours < ttl_hours

    logger.debug(f"Cache check: {file_path} age={age_hours:.1f}h ttl={ttl_hours}h valid={is_valid}")
    return is_valid


from typing import Union, Dict, List

def save_json(data: Union[Dict, List], file_path: str) -> None:
    """
    Save data to a JSON file with pretty formatting.
    Creates parent directories if they don't exist.

    Parameters:
        data: Python dict or list to serialize
        file_path: Target file path (relative or absolute)
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"Saved JSON: {file_path}")


def load_json(file_path: str) -> Union[Dict, List]:
    """
    Load and parse a JSON file.

    Parameters:
        file_path: Path to the JSON file

    Returns:
        Parsed dict or list

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file isn't valid JSON
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Date & Time Helpers ────────────────────────────────────

def format_date_human(iso_str: str) -> str:
    """Converts ISO 8601 to 'March 25, 2026'"""
    if not iso_str or iso_str == "N/A":
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%B %d, %Y")
    except:
        return iso_str

def format_datetime_human(iso_str: str) -> str:
    """Converts ISO 8601 to 'March 25, 2026, 8:19 PM'"""
    if not iso_str or iso_str == "N/A":
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        # Localize if possible or just standard format
        return dt.strftime("%B %d, %Y, %I:%M %p")
    except:
        return iso_str

def get_week_info(iso_str: str) -> str:
    """Converts ISO 8601 to 'Week 2026-W13'"""
    if not iso_str or iso_str == "N/A":
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        year, week, day = dt.isocalendar()
        return f"Week {year}-W{week:02d}"
    except:
        return "N/A"

import emoji
from langdetect import detect, DetectorFactory

# Ensure langdetect results are deterministic
DetectorFactory.seed = 0

def is_english_strict(text: str) -> bool:
    """
    Checks if a text is strictly English.
    Rule 1: langdetect must return 'en'.
    Rule 2: Every word must contain only Latin characters, digits, or common punctuation.
    """
    if not text:
        return False
    
    # Basic langdetect check
    try:
        if detect(text) != 'en':
            return False
    except:
        return False
    
    # Strict word check: any non-Latin character (like Hindi/Devanagari) in any word is a fail.
    # Exclude common punctuation and symbols.
    for word in text.split():
        # Check if word contains any characters outside common Latin/Symbol ranges.
        # This effectively blocks Hinglish/Hindi scripts.
        if any(ord(char) > 127 and not emoji.is_emoji(char) for char in word):
            return False
            
    return True


def count_emojis(text: str) -> int:
    """
    Counts the number of unique or total emojis in a text.
    """
    return len(emoji.emoji_list(text))


def format_pulse_for_dispatch(pulse: dict) -> str:
    """
    Convert pulse JSON into a high-end, visual report for Google Docs / email.
    Inspired by IndMoney/ProductPulse styles.
    """
    generated_at = format_datetime_human(pulse.get('generated_at', 'N/A'))
    period_str = pulse.get('period', 'Current Week')
    week_str = get_week_info(pulse.get('generated_at', datetime.now().isoformat()))
    
    lines = []
    lines.append(f"📊 **WeeklyProductPulse — Groww**")
    lines.append(f"{week_str} | {period_str}")
    lines.append("")

    lines.append("📝 **Overview**")
    lines.append(pulse.get("summary", "N/A"))
    lines.append("")
    
    analysis_context = pulse.get("analysis_explanation")
    if analysis_context:
        lines.append(f"*Context: {analysis_context}*")
        lines.append("")

    lines.append("🔍 **Top Themes**")
    full_themes = pulse.get("themes", [])
    top_3_names = pulse.get("top_3_themes", [])
    
    for i, name in enumerate(top_3_names, 1):
        # Find theme stats
        stats = next((t for t in full_themes if t.get("name") == name), None)
        if stats:
            count = stats.get("review_count", "?")
            pct = stats.get("percentage", "?")
            rating = stats.get("average_rating", "?")
            lines.append(f"{i}. **{name}** ({count} reviews • {pct}% • ★{rating})")
        else:
            lines.append(f"{i}. **{name}**")
            
        # Add a relevant quote if it matches the theme (heuristic: first available quote if themes aren't mapped)
        # Note: In a real production system, we'd map quotes to themes specifically.
        # For now, we'll just show the numbering and stats as requested.
    lines.append("")

    lines.append("💬 **Verbatim User Quotes**")
    for q in pulse.get("quotes", []):
        quote_date = format_date_human(q.get('date', ''))
        lines.append(f"> \"{q.get('text', '')}\"")
        lines.append(f"> *(Rating: {q.get('star_rating', '?')}★ • {quote_date})*")
        lines.append("")

    lines.append("💡 **Actionable Insights**")
    for idea in pulse.get("action_ideas", []):
        lines.append(f"√ {idea}")
    
    lines.append("")
    lines.append(f"*Report generated at {generated_at}*")

    return "\n".join(lines)


def format_explainer_for_dispatch(explainer: dict) -> str:
    """
    Convert explainer JSON into a high-end, visual report.
    """
    asset_class = explainer.get('asset_class', 'N/A')
    last_checked = format_date_human(explainer.get('last_checked', 'N/A'))
    
    lines = []
    lines.append(f"⚖️ **Groww Policy Explainer: {asset_class}**")
    lines.append(f"Pipeline Integrity: Zero-Hallucination Mode • {last_checked}")
    lines.append("")
    
    lines.append("📋 **Key Fee/Policy Points**")
    for bullet in explainer.get("explanation_bullets", []):
        lines.append(f"• {bullet}")
    lines.append("")
    
    lines.append("🔗 **Official Documentation Sources**")
    for link in explainer.get("official_links", []):
        lines.append(f"- {link}")
        
    return "\n".join(lines)
