"""
Backward-compat shim. The actual implementation lives in settle_data.py.
"""

from settle_data import (
    load_settlement_curves,
    get_latest_curve as _get_latest_curve,
    get_historical_curves as _get_historical_curves,
    compute_historical_spread as _compute_historical_spread,
    compute_historical_fly as _compute_historical_fly,
    real_zscore,
)


def load_brent_curves():
    return load_settlement_curves("Brent")


def get_latest_curve():
    return _get_latest_curve("Brent")


def get_historical_curves():
    return _get_historical_curves("Brent")


def compute_historical_spread(m_a: int, m_b: int):
    return _compute_historical_spread("Brent", m_a, m_b)


def compute_historical_fly(m_a: int, m_b: int, m_c: int):
    return _compute_historical_fly("Brent", m_a, m_b, m_c)


def get_spread_history_chart_data(m_a: int, m_b: int, days: int = 90):
    """Return spread history + stats for plotting."""
    import pandas as pd
    series = compute_historical_spread(m_a, m_b)
    if series.empty:
        return None

    recent = series.tail(days)
    full = series.tail(252)

    return {
        "dates": recent.index.tolist(),
        "values": recent.values.tolist(),
        "mean": float(full.mean()),
        "std": float(full.std()),
        "last_value": float(recent.iloc[-1]),
        "last_date": recent.index[-1],
    }


def get_fly_history_chart_data(m_a: int, m_b: int, m_c: int, days: int = 90):
    """Return fly history + stats for plotting."""
    series = compute_historical_fly(m_a, m_b, m_c)
    if series.empty:
        return None

    recent = series.tail(days)
    full = series.tail(252)

    return {
        "dates": recent.index.tolist(),
        "values": recent.values.tolist(),
        "mean": float(full.mean()),
        "std": float(full.std()),
        "last_value": float(recent.iloc[-1]),
        "last_date": recent.index[-1],
    }


def get_front_month_history(days: int = 252):
    df = load_settlement_curves("Brent")
    if df.empty or "M1" not in df.columns:
        import pandas as pd
        return pd.Series(dtype=float)
    return df["M1"].dropna().tail(days)