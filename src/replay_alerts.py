"""
Alert generation for Replay Mode.

Takes a replay snapshot and generates the alerts that would have fired
as of that historical date.
"""

from datetime import datetime


def severity_from_zscore(z: float) -> str:
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
    return {
        "CRITICAL": "#E74C3C",
        "HIGH": "#E67E22",
        "MEDIUM": "#F1C40F",
        "LOW": "#5BA8D9",
    }.get(severity, "#8B9DAE")


def generate_replay_alerts(snapshot: dict, max_alerts: int = 10) -> list:
    """
    Run the alerts engine against a historical snapshot.
    Returns list of alert dicts.
    """
    alerts = []
    if not snapshot.get("available"):
        return alerts

    snap_date = snapshot["date"]
    timestamp_str = snap_date.strftime("%H:%M") if hasattr(snap_date, "strftime") else "—"
    instrument_label = snapshot.get("instrument", "Brent")
    # --- Calendar spread alerts ---
    for s in snapshot.get("calendar_spreads", []):
        if abs(s["z_score"]) >= 1.5:
            sev = severity_from_zscore(s["z_score"])
            sign = "+" if s["value"] >= 0 else ""
            alerts.append({
                "severity": sev,
                "category": "SPREAD",
                "headline": f"{instrument_label} {s['name']} {s['status']}",
                "detail": f"At {sign}{s['value']:.2f} · z {s['z_score']:+.1f}σ",
                "source": instrument_label,
                "timestamp": timestamp_str,
                "_sort": abs(s["z_score"]),
            })

    # --- Fly alerts ---
    for f in snapshot.get("flies", []):
        if abs(f["z_score"]) >= 1.5:
            sev = severity_from_zscore(f["z_score"])
            sign = "+" if f["value"] >= 0 else ""
            alerts.append({
                "severity": sev,
                "category": "FLY",
                "headline": f"{instrument_label} {f['name']} {f['status']}",
                "detail": f"At {sign}{f['value']:.2f} ({f['shape']}) · z {f['z_score']:+.1f}σ",
                "source": instrument_label,
                "timestamp": timestamp_str,
                "_sort": abs(f["z_score"]),
            })

    # --- Inter-product alerts ---
    for s in snapshot.get("inter_product", []):
        if abs(s["z_score"]) >= 1.5:
            sev = severity_from_zscore(s["z_score"])
            sign = "+" if s["value"] >= 0 else ""
            alerts.append({
                "severity": sev,
                "category": "INTER-PRODUCT",
                "headline": f"{s['name']} {s['status']}",
                "detail": f"At {sign}{s['value']:.2f} · z {s['z_score']:+.1f}σ",
                "source": "spreads",
                "timestamp": timestamp_str,
                "_sort": abs(s["z_score"]),
            })

    # --- Curve structure alert ---
    curve = snapshot.get("curve", snapshot.get("brent_curve", []))
    if len(curve) >= 12:
        front = curve[0][1]
        m12 = curve[11][1]
        pct_diff = (m12 - front) / front * 100
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
                "headline": f"{instrument_label} {structure}",
                "detail": detail,
                "source": "Brent",
                "timestamp": timestamp_str,
                "_sort": abs(pct_diff) / 5,
            })

    # --- Macro move alerts (significant daily price moves) ---
    macro = snapshot.get("macro", {})
    for name, info in macro.items():
        if name.startswith("_"):
            continue
        if not isinstance(info, dict):
            continue
        latest = info.get("latest", 0)
        change = info.get("change", 0)
        if latest == 0:
            continue
        pct_move = (change / latest) * 100
        if abs(pct_move) >= 3:
            direction = "up" if pct_move > 0 else "down"
            sev = "HIGH" if abs(pct_move) >= 5 else "MEDIUM"
            alerts.append({
                "severity": sev,
                "category": "PRICE MOVE",
                "headline": f"{name} {direction} {abs(pct_move):.1f}% daily",
                "detail": f"From {info['previous']:.2f} to {latest:.2f}",
                "source": name,
                "timestamp": timestamp_str,
                "_sort": abs(pct_move) / 3,
            })

    # Sort and trim
    severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    alerts.sort(key=lambda a: (severity_rank.get(a["severity"], 9), -a["_sort"]))
    for a in alerts:
        a.pop("_sort", None)

    return alerts[:max_alerts]