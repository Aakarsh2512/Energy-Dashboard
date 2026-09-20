"""
Alerts engine for the Energy Trading Dashboard.

Generates real-time alerts based on:
- Spread/fly z-score breaches
- Correlation breaks
- Future: inventory surprises, gamma map flips, etc.

Each alert has: severity, category, headline, detail, timestamp.
"""

import streamlit as st
from datetime import datetime


def severity_from_zscore(z: float) -> str:
    """Map absolute z-score to severity label."""
    abs_z = abs(z)
    if abs_z >= 2.5:
        return "CRITICAL"
    elif abs_z >= 2.0:
        return "HIGH"
    elif abs_z >= 1.5:
        return "MEDIUM"
    else:
        return "LOW"


def severity_color(severity: str) -> str:
    """Hex color for each severity level."""
    return {
        "CRITICAL": "#E74C3C",
        "HIGH": "#E67E22",
        "MEDIUM": "#F1C40F",
        "LOW": "#5BA8D9",
    }.get(severity, "#8B9DAE")


def generate_alerts(market_data: dict, max_alerts: int = 8) -> list:
    """
    Generate the current alert list. Each alert is a dict with:
    - severity, category, headline, detail, source, timestamp
    """
    alerts = []
    now = datetime.now().strftime("%H:%M")

    # --------------------------------------------------------
    # 1. Spread alerts (calendar + inter-product) — Brent gets real z-scores
    # --------------------------------------------------------
    try:
        from spreads_flies import (
            compute_calendar_spreads_table,
            compute_flies,
            compute_interproduct_spreads_table,
        )

        for instrument in ["Brent", "WTI"]:
            cal_spreads = compute_calendar_spreads_table(market_data, instrument)
            for s in cal_spreads:
                if abs(s["z_score"]) >= 1.5:
                    sev = severity_from_zscore(s["z_score"])
                    sign = "+" if s["value"] >= 0 else ""
                    alerts.append({
                        "severity": sev,
                        "category": "SPREAD",
                        "headline": f"{instrument} {s['name']} {s['status']}",
                        "detail": f"At {sign}{s['value']:.2f} · z {s['z_score']:+.1f}σ",
                        "source": instrument,
                        "timestamp": now,
                        "_sort": abs(s["z_score"]),
                    })

            flies = compute_flies(market_data, instrument)
            for f in flies:
                if abs(f["z_score"]) >= 1.5:
                    sev = severity_from_zscore(f["z_score"])
                    sign = "+" if f["value"] >= 0 else ""
                    alerts.append({
                        "severity": sev,
                        "category": "FLY",
                        "headline": f"{instrument} {f['name']} {f['status']}",
                        "detail": f"At {sign}{f['value']:.2f} ({f['shape']}) · z {f['z_score']:+.1f}σ",
                        "source": instrument,
                        "timestamp": now,
                        "_sort": abs(f["z_score"]),
                    })

        # Inter-product spreads (real)
        ip_spreads = compute_interproduct_spreads_table(market_data)
        for s in ip_spreads:
            if abs(s["z_score"]) >= 1.5:
                sev = severity_from_zscore(s["z_score"])
                sign = "+" if s["value"] >= 0 else ""
                alerts.append({
                    "severity": sev,
                    "category": "INTER-PRODUCT",
                    "headline": f"{s['name']} {s['status']}",
                    "detail": f"At {sign}{s['value']:.2f} · z {s['z_score']:+.1f}σ",
                    "source": "spreads",
                    "timestamp": now,
                    "_sort": abs(s["z_score"]),
                })
    except Exception as e:
        print(f"[alerts] spreads error: {e}")

    # --------------------------------------------------------
    # 2. Correlation alerts — significant shifts vs prior window
    # --------------------------------------------------------
    try:
        from correlations import (
            fetch_correlation_data,
            compute_correlation_change,
            find_correlation_breaks,
        )

        prices = fetch_correlation_data(window_days=30)
        if not prices.empty:
            delta = compute_correlation_change(prices, window_days=30, lookback_days=30)
            if not delta.empty:
                breaks = find_correlation_breaks(delta, threshold=0.3)
                for b in breaks[:3]:  # top 3 only
                    abs_delta = abs(b["delta"])
                    if abs_delta >= 0.4:
                        sev = "HIGH"
                    elif abs_delta >= 0.3:
                        sev = "MEDIUM"
                    else:
                        continue

                    alerts.append({
                        "severity": sev,
                        "category": "CORRELATION",
                        "headline": f"{b['pair']} {b['direction']}",
                        "detail": f"Δρ {b['delta']:+.2f} vs prior 30d window",
                        "source": "correlation",
                        "timestamp": now,
                        "_sort": abs_delta * 2,  # scale for sorting
                    })
    except Exception as e:
        print(f"[alerts] correlation error: {e}")

    # --------------------------------------------------------
    # 3. Curve structure alerts (extreme contango/backwardation in front)
    # --------------------------------------------------------
    try:
        from forward_curves import build_curve_for_instrument, classify_curve_structure

        for instrument in ["Brent", "WTI"]:
            curve = build_curve_for_instrument(instrument, market_data)
            if not curve or len(curve) < 12:
                continue

            front = curve[0][1]
            m12 = curve[11][1]
            pct_diff = (m12 - front) / front * 100

            # Extreme contango/backwardation alert
            if abs(pct_diff) >= 8:
                if pct_diff > 0:
                    structure = "STEEP CONTANGO"
                    detail = f"Front-M12 spread −{abs(pct_diff):.1f}% · oversupply signal"
                else:
                    structure = "DEEP BACKWARDATION"
                    detail = f"Front-M12 spread +{abs(pct_diff):.1f}% · tight market signal"

                alerts.append({
                    "severity": "HIGH" if abs(pct_diff) >= 12 else "MEDIUM",
                    "category": "CURVE",
                    "headline": f"{instrument} {structure}",
                    "detail": detail,
                    "source": instrument,
                    "timestamp": now,
                    "_sort": abs(pct_diff) / 5,
                })
    except Exception as e:
        print(f"[alerts] curve error: {e}")

    # --------------------------------------------------------
    # Sort by severity then magnitude
    # --------------------------------------------------------
    severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    alerts.sort(key=lambda a: (severity_rank.get(a["severity"], 9), -a["_sort"]))

    # Strip internal sort key and return top N
    for a in alerts:
        a.pop("_sort", None)

    return alerts[:max_alerts]


def alert_summary(alerts: list) -> dict:
    """Count alerts by severity."""
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for a in alerts:
        sev = a.get("severity", "LOW")
        counts[sev] = counts.get(sev, 0) + 1
    counts["total"] = sum(counts.values())
    return counts