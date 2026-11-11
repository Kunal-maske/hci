"""
Zero-dependency .env loader for CS 435 AI Interview Practice System.
Automatically loads and reloads environment variables from project root .env file.
Requires no external dependencies and runs reliably across all Python environments.
"""
import os
from pathlib import Path
from typing import Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOTENV_PATH = PROJECT_ROOT / ".env"


def load_dotenv_file(filepath: Path = DOTENV_PATH) -> Dict[str, str]:
    """
    Parses key=value pairs from the .env file and injects them into os.environ.
    Preserves existing non-empty values unless specified.
    """
    loaded = {}
    if not filepath.exists():
        return loaded

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key:
                        os.environ[key] = val
                        loaded[key] = val
    except Exception:
        pass
    return loaded


def get_env_variable(key: str, default: str = "") -> str:
    """
    Retrieves an environment variable, refreshing from .env if currently empty.
    """
    val = os.environ.get(key, "").strip()
    if not val and DOTENV_PATH.exists():
        load_dotenv_file(DOTENV_PATH)
        val = os.environ.get(key, "").strip()
    return val or default


# Auto-load on import
load_dotenv_file()
