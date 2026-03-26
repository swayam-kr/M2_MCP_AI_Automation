import os
import yaml
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env FIRST (before any other imports might need env vars)
load_dotenv()

from typing import Dict, Any, Optional

def _load_yaml_config() -> Dict[str, Any]:
    """
    Reads config.yaml from project root.
    Returns parsed dict.
    Raises FileNotFoundError if config.yaml missing.
    """
    # Assuming config.yaml is in the same directory as the backend folder
    config_path = Path(__file__).parent.parent / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"config.yaml not found at {config_path}")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def _merge_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Overrides specific config values with environment variables.
    Priority: .env > config.yaml
    """
    # Override Google Docs document ID
    doc_id = os.getenv("GOOGLE_DOCS_DOC_ID")
    if doc_id:
        if "mcp" not in config: config["mcp"] = {}
        if "google_docs" not in config["mcp"]: config["mcp"]["google_docs"] = {}
        config["mcp"]["google_docs"]["document_id"] = doc_id

    # Override log level
    log_level = os.getenv("LOG_LEVEL")
    if log_level:
        if "app" not in config: config["app"] = {}
        config["app"]["log_level"] = log_level

    return config


def get_setting(dotpath: str, default=None):
    """
    Access nested config values using dot notation.

    Example:
        get_setting("part_a.max_weeks")  -> 8
        get_setting("llm.groq.model")    -> "llama3-70b-8192"

    Parameters:
        dotpath: Dot-separated path like "section.subsection.key"
        default: Value to return if path not found

    Returns:
        The config value, or default if not found.
    """
    keys = dotpath.split(".")
    value = settings
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value


logger = logging.getLogger("config")

# ── Module-level initialization ──
try:
    settings = _load_yaml_config()
    settings = _merge_env_overrides(settings)
except Exception as e:
    # Fallback to empty if loading fails during setup
    settings = {}
    logger.warning(f"Failed to load config.yaml: {e}")

# Configure logging
log_level_name = get_setting("app.log_level", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level_name, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger.info("Config initialized.")
