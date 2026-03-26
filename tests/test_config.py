import sys
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

def test_config_loads_without_error():
    """Config module should import without raising."""
    from backend.config import settings
    assert isinstance(settings, dict)

def test_config_has_app_name():
    """Config must have app.name."""
    from backend.config import settings
    assert settings.get("app", {}).get("name") == "AI Ops Automator"

def test_get_setting_dot_notation():
    """get_setting should support dot-notation access."""
    from backend.config import get_setting
    assert get_setting("part_a.max_weeks") == 8
    assert get_setting("llm.groq.model") == "llama-3.3-70b-versatile"

def test_get_setting_default():
    """get_setting should return default for missing keys."""
    from backend.config import get_setting
    assert get_setting("nonexistent.key", "fallback") == "fallback"
