"""
News data interface for the Energy Trading Dashboard.

This module is a thin facade over news_worker.py — the actual fetching and
LLM tagging happens in a background daemon thread to avoid blocking the
Streamlit UI thread.

Public API:
    get_tagged_news()           — returns list of currently-cached headlines
    get_worker_status()         — returns worker status dict
    summarize_sentiment(news)   — sentiment summary from a list of tagged news
    ensure_worker_running()     — idempotent: starts worker if not already running
"""

from news_worker import (
    ensure_worker_running,
    get_tagged_news,
    get_worker_status,
)


# Start the worker as soon as this module is first imported.
# Safe to import many times — only starts once.
ensure_worker_running()


def summarize_sentiment(tagged_news: list) -> dict:
    """Compute sentiment summary across a list of tagged headlines."""
    if not tagged_news:
        return {"bullish": 0, "bearish": 0, "neutral": 0, "net_score": 0, "total": 0}

    counts = {"bullish": 0, "bearish": 0, "neutral": 0}
    for item in tagged_news:
        # Only count actually-tagged headlines toward sentiment
        if not item.get("is_tagged"):
            continue
        direction = item.get("tags", {}).get("direction", "neutral")
        counts[direction] = counts.get(direction, 0) + 1

    total = sum(counts.values())
    net_score = ((counts["bullish"] - counts["bearish"]) / total * 100) if total > 0 else 0

    return {**counts, "net_score": net_score, "total": total}