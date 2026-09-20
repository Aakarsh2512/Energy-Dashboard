"""
Strategy persistence — save/load user-built strategies to JSON.

Strategies are stored in data/saved_strategies.json as a dict keyed by name.
Each entry is a full strategy config dict (same schema as run_backtest expects).
"""

import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
STORE_PATH = PROJECT_ROOT / "data" / "saved_strategies.json"


def _load_all() -> dict:
    """Load the full saved-strategies dict (or empty)."""
    if not STORE_PATH.exists():
        return {}
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[strategy_store] Load error: {e}")
        return {}


def _save_all(strategies: dict):
    """Write the full dict back to disk."""
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(strategies, f, indent=2, default=str)


def list_strategies() -> list:
    """Return list of saved strategy names, sorted by saved date desc."""
    data = _load_all()
    items = sorted(
        data.items(),
        key=lambda kv: kv[1].get("saved_at", ""),
        reverse=True,
    )
    return [name for name, _ in items]


def save_strategy(name: str, config: dict) -> bool:
    """Save (or overwrite) a strategy by name. Returns True on success."""
    if not name or not name.strip():
        return False

    name = name.strip()
    data = _load_all()

    # Stamp it
    config = dict(config)
    config["saved_at"] = datetime.now().isoformat(timespec="seconds")
    config["name"] = name

    data[name] = config
    _save_all(data)
    return True


def load_strategy(name: str) -> dict:
    """Return strategy config by name, or empty dict if not found."""
    data = _load_all()
    return data.get(name, {})


def delete_strategy(name: str) -> bool:
    """Remove a strategy by name. Returns True if found."""
    data = _load_all()
    if name in data:
        del data[name]
        _save_all(data)
        return True
    return False