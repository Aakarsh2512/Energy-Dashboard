"""
Background news tagging worker.

Runs in a daemon thread inside the Streamlit process. Polls the RSS feed
periodically, tags new headlines via Gemini, and writes results to a
thread-safe in-memory cache.

The Streamlit UI thread only reads from the cache — never blocks on LLM calls.
This is the production-correct pattern.
"""

import os
import json
import time
import threading
import requests
import feedparser
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Toggle: only call Gemini when tagging is explicitly enabled.
# Set ENABLE_NEWS_TAGGING=true in .env to activate before a demo.
ENABLE_NEWS_TAGGING = os.getenv("ENABLE_NEWS_TAGGING", "false").strip().lower() == "true"
FEED_URL = "https://www.financialjuice.com/feed.ashx?xy=rss"
GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


# Thread-safe cache
_cache_lock = threading.Lock()
_news_cache = {
    "headlines": [],            # list of tagged headline dicts
    "last_fetch": None,         # datetime of last RSS poll
    "last_tag_count": 0,        # how many tagged in last cycle
    "tag_in_progress": False,   # are we currently tagging?
    "worker_started": False,    # has the worker thread been started?
    "status": "initializing",   # status string for UI
}

# Internal state (not exposed to UI)
_tagged_titles = set()  # titles we've already tagged this session


TAGGING_INSTRUCTIONS = """You are an expert energy markets analyst. Classify how this news headline likely affects energy futures.

Return a JSON object with these fields:
- direction: "bullish" | "bearish" | "neutral" (impact on crude oil)
- contracts: array from ["WTI", "Brent", "NatGas", "RBOB", "ULSD"] (empty if not energy-relevant)
- magnitude: "minor" | "moderate" | "major"
- confidence: float 0.0 to 1.0
- reaction: one short sentence on how a trader might react (max 20 words)
- reasoning: brief explanation (max 25 words)

Classification rules:
- Supply disruptions, OPEC cuts, sanctions, geopolitical tension -> bullish
- Demand weakness, inventory builds, production increases, recession signals -> bearish
- Non-energy headlines (table headers, currency moves) -> neutral with low confidence
- Vague headlines -> neutral

Headline to classify: """


def _tag_headline(headline: str):
    """Call Gemini to tag a headline. Returns dict or None. Never raises."""
    if not GEMINI_API_KEY:
        return None
    if not ENABLE_NEWS_TAGGING:
        return None
    url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": TAGGING_INSTRUCTIONS + headline}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 400,
            "responseMimeType": "application/json",
        },
    }

    try:
        response = requests.post(url, json=payload, timeout=20)
        if response.status_code != 200:
            print(f"[news_worker] Gemini HTTP {response.status_code}: {response.text[:120]}")
            return None

        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return None

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return None

        raw = parts[0].get("text", "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        return json.loads(raw)
    except Exception as e:
        print(f"[news_worker] Tag error: {type(e).__name__}: {str(e)[:80]}")
        return None


def _fetch_rss():
    """Fetch headlines from FinancialJuice RSS. Returns list of dicts."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(FEED_URL, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"[news_worker] RSS HTTP {resp.status_code}")
            return []

        feed = feedparser.parse(resp.content)
        items = []
        for entry in feed.entries[:50]:
            items.append({
                "title": entry.get("title", ""),
                "published": entry.get("published", ""),
                "link": entry.get("link", ""),
            })
        return items
    except Exception as e:
        print(f"[news_worker] RSS error: {type(e).__name__}: {e}")
        return []


def _untagged_fallback(item):
    """Build a fallback 'untagged' entry so a headline still displays before LLM tags it."""
    return {
        **item,
        "tags": {
            "direction": "neutral",
            "contracts": [],
            "magnitude": "minor",
            "confidence": 0.0,
            "reaction": "Awaiting LLM tagging...",
            "reasoning": "",
        },
        "is_tagged": False,
    }


def _worker_loop():
    """The background loop. Runs forever in a daemon thread."""
    print("[news_worker] Worker thread started")
    """Main worker loop — runs in background thread."""
    if not ENABLE_NEWS_TAGGING:
        print("[news_worker] Tagging DISABLED (ENABLE_NEWS_TAGGING=false). "
              "Set to 'true' in .env to enable Gemini tagging.")
    else:
        print("[news_worker] Tagging ENABLED. Gemini calls will be made.")

    while True:
        try:
            _run_one_cycle()
        except Exception as e:
            print(f"[news_worker] Cycle error: {type(e).__name__}: {e}")
            with _cache_lock:
                _news_cache["status"] = f"error: {type(e).__name__}"

        # Wait 90 seconds before next cycle
        time.sleep(90)


def _run_one_cycle():
    """One fetch-and-tag cycle."""
    with _cache_lock:
        _news_cache["status"] = "fetching rss"

    headlines = _fetch_rss()
    if not headlines:
        with _cache_lock:
            _news_cache["status"] = "rss empty"
        return

    with _cache_lock:
        _news_cache["last_fetch"] = datetime.now()
        # Show untagged headlines immediately so the UI isn't empty
        existing_tagged = {h["title"]: h for h in _news_cache["headlines"] if h.get("is_tagged")}
        merged = []
        for item in headlines:
            if item["title"] in existing_tagged:
                merged.append(existing_tagged[item["title"]])
            else:
                merged.append(_untagged_fallback(item))
        _news_cache["headlines"] = merged
        _news_cache["status"] = f"showing {len(merged)} headlines (tagging in background)"

    # Tag any headlines we haven't tagged yet, up to 20 per cycle
    untagged_now = [h for h in headlines if h["title"] not in _tagged_titles]

    with _cache_lock:
        _news_cache["tag_in_progress"] = True

    tagged_this_cycle = 0
    for item in untagged_now[:20]:  # tag up to 20 per cycle
        tags = _tag_headline(item["title"])

        if tags is None:
            # Skip — will retry next cycle
            time.sleep(4.5)
            continue

        tagged_item = {**item, "tags": tags, "is_tagged": True}
        _tagged_titles.add(item["title"])
        tagged_this_cycle += 1

        # Update cache after each successful tag
        with _cache_lock:
            for i, h in enumerate(_news_cache["headlines"]):
                if h["title"] == item["title"]:
                    _news_cache["headlines"][i] = tagged_item
                    break
            _news_cache["status"] = (
                f"tagged {tagged_this_cycle}/{len(untagged_now[:20])} this cycle"
            )

        time.sleep(4.5)  # respect 15 RPM rate limit

    with _cache_lock:
        _news_cache["tag_in_progress"] = False
        _news_cache["last_tag_count"] = tagged_this_cycle
        _news_cache["status"] = f"idle · last cycle tagged {tagged_this_cycle}"

    print(f"[news_worker] Cycle complete: tagged {tagged_this_cycle} new headlines")


def ensure_worker_running():
    """Start the worker thread if not already running. Safe to call repeatedly."""
    with _cache_lock:
        if _news_cache["worker_started"]:
            return
        _news_cache["worker_started"] = True

    thread = threading.Thread(target=_worker_loop, daemon=True, name="news_worker")
    thread.start()
    print("[news_worker] Started background daemon thread")


def get_tagged_news() -> list:
    """Return current cached headlines. Returns immediately, never blocks."""
    with _cache_lock:
        return list(_news_cache["headlines"])


def get_worker_status() -> dict:
    """Return cache status for debugging / UI display."""
    with _cache_lock:
        return {
            "status": _news_cache["status"],
            "headline_count": len(_news_cache["headlines"]),
            "tagged_count": sum(1 for h in _news_cache["headlines"] if h.get("is_tagged")),
            "last_fetch": _news_cache["last_fetch"],
            "tag_in_progress": _news_cache["tag_in_progress"],
        }