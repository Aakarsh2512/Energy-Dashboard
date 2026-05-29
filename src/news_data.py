"""
News fetching and LLM tagging for the Energy Trading Dashboard.

Pulls headlines from FinancialJuice RSS and tags each with Groq (Llama 3.3 70B)
for direction, affected contracts, magnitude, confidence, and trader reaction.
"""

import os
import json
import time
import feedparser
import streamlit as st
from groq import Groq
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

FEED_URL = "https://www.financialjuice.com/feed.ashx?xy=rss"

TAGGING_SYSTEM_PROMPT = """You are an expert energy markets analyst. You analyze news headlines and classify their likely impact on energy futures.

For each headline, respond with ONLY a JSON object (no other text) with these fields:
- "direction": one of "bullish", "bearish", "neutral" (overall impact on crude oil)
- "contracts": list of affected contracts from ["WTI", "Brent", "NatGas", "RBOB", "ULSD"]
- "magnitude": one of "minor", "moderate", "major"
- "confidence": float 0.0 to 1.0
- "reaction": a one-sentence note on how a trader might react (max 20 words)
- "reasoning": a brief explanation (max 25 words)

Rules:
- "bullish" means the news likely pushes prices UP
- "bearish" means likely pushes prices DOWN
- Supply disruptions, OPEC cuts, sanctions = usually bullish
- Demand weakness, inventory builds, production increases = usually bearish
- Be decisive but honest about confidence. Vague headlines get low confidence and "neutral"."""


def _get_client():
    if not GROQ_API_KEY:
        return None
    return Groq(api_key=GROQ_API_KEY)


@st.cache_data(ttl=300)  # cache news for 5 minutes
def fetch_news(max_items: int = 20) -> list:
    """Pull headlines from FinancialJuice RSS feed."""
    try:
        feed = feedparser.parse(FEED_URL)
        items = []
        for entry in feed.entries[:max_items]:
            items.append({
                "title": entry.get("title", ""),
                "published": entry.get("published", ""),
                "link": entry.get("link", ""),
            })
        return items
    except Exception as e:
        print(f"[news_data] RSS fetch error: {e}")
        return []


def tag_headline(headline: str) -> dict:
    """Tag a single headline with the LLM. Returns a dict or None."""
    client = _get_client()
    if client is None:
        return None

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": TAGGING_SYSTEM_PROMPT},
                {"role": "user", "content": f"Headline: {headline}"},
            ],
            max_tokens=300,
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        return json.loads(raw)
    except Exception as e:
        print(f"[news_data] Tagging error: {e}")
        return None


@st.cache_data(ttl=300)  # cache tagged news for 5 minutes
def fetch_and_tag_news(max_to_tag: int = 12) -> list:
    """Pull headlines and tag each one. Cached so we don't re-call the LLM constantly."""
    news = fetch_news(max_items=max_to_tag)
    tagged = []

    for item in news:
        tags = tag_headline(item["title"])
        if tags:
            tagged.append({**item, "tags": tags})
        else:
            # Include untagged item with neutral default so it still shows
            tagged.append({
                **item,
                "tags": {
                    "direction": "neutral",
                    "contracts": [],
                    "magnitude": "minor",
                    "confidence": 0.0,
                    "reaction": "Could not classify.",
                    "reasoning": "",
                },
            })
        time.sleep(0.3)  # gentle pacing for free tier

    return tagged


def summarize_sentiment(tagged_news: list) -> dict:
    """Compute an overall sentiment summary across all tagged headlines."""
    if not tagged_news:
        return {"bullish": 0, "bearish": 0, "neutral": 0, "net_score": 0}

    counts = {"bullish": 0, "bearish": 0, "neutral": 0}
    for item in tagged_news:
        direction = item["tags"].get("direction", "neutral")
        counts[direction] = counts.get(direction, 0) + 1

    total = sum(counts.values())
    net_score = ((counts["bullish"] - counts["bearish"]) / total * 100) if total > 0 else 0

    return {**counts, "net_score": net_score, "total": total}