"""
Strategy Backtest Engine.

Takes a strategy config (rules dict) and runs it against real historical
settlement data, returning trade-by-trade results and aggregate statistics.

Strategy config schema:
{
    "name": "Brent M1-M2 Mean Reversion",
    "signal": {
        "type": "z_score",  # or "curve_shape" or "price"
        "instrument": "Brent",
        "metric": "spread_M1_M2",  # or "spread_M1_M3", "fly_M1_M2_M3", "front_to_M12_pct"
        "lookback_days": 252,
        "entry_threshold": 2.0,    # in units of σ
        "entry_direction": "above", # "above" or "below"
    },
    "position": {
        "structure": "calendar_spread",  # or "fly", "outright"
        "direction": "short",  # "long" or "short" — what to do when signal fires
        # for calendar_spread: short sells M_a, buys M_b
        # for outright: long buys, short sells
    },
    "exit": {
        "rules": ["mean_revert", "time_stop"],  # any combo
        "mean_revert_target": "mean",  # exit when value returns to μ
        "time_stop_days": 20,
        "profit_target_pct": None,  # e.g., 0.05 for +5%
        "stop_loss_pct": None,      # e.g., -0.03 for -3%
    },
    "lookback_years": 5,  # how much history to backtest
}

Returns:
{
    "trades": [...],         # list of trade dicts
    "stats": {...},          # aggregate stats
    "equity_curve": [...],   # cumulative PnL over time
    "rule_signal_series": ...# the signal time series for the chart
}
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from settle_data import load_settlement_curves


# ============================================================
# SIGNAL EXTRACTORS
# ============================================================

def get_signal_series(signal_config: dict) -> pd.Series:
    """
    Compute the signal time series based on config.
    Returns a Series indexed by date with the signal value at each date.
    """
    instrument = signal_config["instrument"]
    metric = signal_config["metric"]

    df = load_settlement_curves(instrument)
    if df.empty:
        return pd.Series(dtype=float)

    # Spread signals
    if metric.startswith("spread_M"):
        # parse "spread_M1_M2" -> a=1, b=2
        parts = metric.replace("spread_M", "").split("_M")
        a, b = int(parts[0]), int(parts[1])
        col_a, col_b = f"M{a}", f"M{b}"
        if col_a not in df.columns or col_b not in df.columns:
            return pd.Series(dtype=float)
        return (df[col_a] - df[col_b]).dropna()

    # Fly signals
    if metric.startswith("fly_M"):
        # parse "fly_M1_M2_M3" -> a=1, b=2, c=3
        parts = metric.replace("fly_M", "").split("_M")
        a, b, c = int(parts[0]), int(parts[1]), int(parts[2])
        cols = [f"M{a}", f"M{b}", f"M{c}"]
        if not all(col in df.columns for col in cols):
            return pd.Series(dtype=float)
        return (df[cols[0]] - 2 * df[cols[1]] + df[cols[2]]).dropna()

    # Front-to-M12 curve structure pct
    if metric == "front_to_M12_pct":
        if "M1" not in df.columns or "M12" not in df.columns:
            return pd.Series(dtype=float)
        return ((df["M1"] - df["M12"]) / df["M12"] * 100).dropna()

    # Front month price
    if metric == "front_price":
        if "M1" not in df.columns:
            return pd.Series(dtype=float)
        return df["M1"].dropna()

    # Front month % deviation from N-day moving average
    if metric.startswith("front_vs_ma_"):
        # parse "front_vs_ma_60" -> N=60
        n = int(metric.replace("front_vs_ma_", ""))
        if "M1" not in df.columns:
            return pd.Series(dtype=float)
        m1 = df["M1"].dropna()
        ma = m1.rolling(n).mean()
        return ((m1 - ma) / ma * 100).dropna()

    return pd.Series(dtype=float)


def get_z_score_series(signal_series: pd.Series, lookback_days: int) -> pd.Series:
    """Convert raw signal series to a rolling z-score series."""
    rolling_mean = signal_series.rolling(lookback_days, min_periods=30).mean()
    rolling_std = signal_series.rolling(lookback_days, min_periods=30).std()
    z = (signal_series - rolling_mean) / rolling_std
    return z.dropna()


# ============================================================
# POSITION VALUER (P/L computation)
# ============================================================

def get_position_value(position_config: dict, signal_config: dict, date) -> float:
    """
    Return the dollar value of one unit of this position at the given date.
    For a calendar spread M_a - M_b: return spot value of that spread.
    For an outright: return the front month price.
    """
    instrument = signal_config["instrument"]
    df = load_settlement_curves(instrument)
    if df.empty:
        return 0.0

    target = pd.to_datetime(date)
    valid = df.index[df.index <= target]
    if len(valid) == 0:
        return 0.0
    row = df.loc[valid[-1]]

    structure = position_config["structure"]
    metric = signal_config["metric"]

    if structure == "calendar_spread" and metric.startswith("spread_M"):
        parts = metric.replace("spread_M", "").split("_M")
        a, b = int(parts[0]), int(parts[1])
        return float(row[f"M{a}"] - row[f"M{b}"])

    if structure == "fly" and metric.startswith("fly_M"):
        parts = metric.replace("fly_M", "").split("_M")
        a, b, c = int(parts[0]), int(parts[1]), int(parts[2])
        return float(row[f"M{a}"] - 2 * row[f"M{b}"] + row[f"M{c}"])

    if structure == "outright":
        return float(row["M1"]) if "M1" in df.columns else 0.0

    return 0.0


# ============================================================
# THE BACKTEST RUNNER
# ============================================================

def run_backtest(strategy: dict) -> dict:
    """
    Run a full backtest of the given strategy config against real history.
    Returns dict with trades, stats, equity_curve, and signal series.
    """
    signal_cfg = strategy["signal"]
    position_cfg = strategy["position"]
    exit_cfg = strategy["exit"]
    lookback_years = strategy.get("lookback_years", 5)

    # ============================================================
    # 1. Compute signal series + z-score series
    # ============================================================
    signal_series = get_signal_series(signal_cfg)
    if signal_series.empty:
        return _empty_result("No data for signal")

    sig_type = signal_cfg["type"]

    if sig_type == "z_score":
        z_series = get_z_score_series(signal_series, signal_cfg["lookback_days"])
        comparator_series = z_series
        threshold = signal_cfg["entry_threshold"]
    elif sig_type == "curve_shape":
        # signal_series IS the raw value (e.g., front_to_M12_pct)
        comparator_series = signal_series
        threshold = signal_cfg["entry_threshold"]
    elif sig_type == "price":
        # signal_series IS the % deviation or price
        comparator_series = signal_series
        threshold = signal_cfg["entry_threshold"]
    else:
        return _empty_result(f"Unknown signal type: {sig_type}")

    # ============================================================
    # 2. Restrict to lookback window
    # ============================================================
    end_date = comparator_series.index[-1]
    start_date = end_date - pd.DateOffset(years=lookback_years)
    comparator_series = comparator_series[comparator_series.index >= start_date]

    if comparator_series.empty:
        return _empty_result("No data in lookback window")

    # ============================================================
    # 3. Iterate through history, identify entry/exit events
    # ============================================================
    entry_direction = signal_cfg["entry_direction"]
    position_dir = position_cfg["direction"]  # "long" or "short"

    trades = []
    in_position = False
    entry_date = None
    entry_value = None
    entry_signal = None
    days_in_trade = 0

    # Mean for "mean_revert" exit
    rolling_mean = signal_series.rolling(signal_cfg.get("lookback_days", 252),
                                          min_periods=30).mean()

    for date, comp_value in comparator_series.items():
        if pd.isna(comp_value):
            continue

        # Check for entry
        if not in_position:
            entry_triggered = False
            if entry_direction == "above" and comp_value > threshold:
                entry_triggered = True
            elif entry_direction == "below" and comp_value < threshold:
                entry_triggered = True

            if entry_triggered:
                in_position = True
                entry_date = date
                entry_value = get_position_value(position_cfg, signal_cfg, date)
                entry_signal = comp_value
                days_in_trade = 0
            continue

        # In position: check exit conditions
        days_in_trade += 1
        current_value = get_position_value(position_cfg, signal_cfg, date)

        exit_triggered = False
        exit_reason = ""

        exit_rules = exit_cfg.get("rules", [])

        if "time_stop" in exit_rules and days_in_trade >= exit_cfg.get("time_stop_days", 20):
            exit_triggered = True
            exit_reason = f"Time stop ({days_in_trade}d)"

        if not exit_triggered and "mean_revert" in exit_rules:
            mean_at_date = rolling_mean.get(date, np.nan)
            if pd.notna(mean_at_date):
                # For "above" entry, exit when raw signal returns to mean
                raw_value = signal_series.get(date, np.nan)
                if pd.notna(raw_value):
                    if entry_direction == "above" and raw_value <= mean_at_date:
                        exit_triggered = True
                        exit_reason = "Reverted to mean"
                    elif entry_direction == "below" and raw_value >= mean_at_date:
                        exit_triggered = True
                        exit_reason = "Reverted to mean"

        if not exit_triggered and "signal_reverse" in exit_rules:
            # Exit when signal crosses back across threshold
            if entry_direction == "above" and comp_value < threshold:
                exit_triggered = True
                exit_reason = "Signal reversed"
            elif entry_direction == "below" and comp_value > threshold:
                exit_triggered = True
                exit_reason = "Signal reversed"

        if not exit_triggered and exit_cfg.get("profit_target_pct") is not None:
            target_pct = exit_cfg["profit_target_pct"]
            # PnL is direction-aware
            pnl_per_unit = (current_value - entry_value) if position_dir == "long" else (entry_value - current_value)
            if entry_value != 0 and (pnl_per_unit / abs(entry_value)) >= target_pct:
                exit_triggered = True
                exit_reason = f"Profit target ({target_pct*100:.1f}%)"

        if not exit_triggered and exit_cfg.get("stop_loss_pct") is not None:
            stop_pct = exit_cfg["stop_loss_pct"]
            pnl_per_unit = (current_value - entry_value) if position_dir == "long" else (entry_value - current_value)
            if entry_value != 0 and (pnl_per_unit / abs(entry_value)) <= stop_pct:
                exit_triggered = True
                exit_reason = f"Stop loss ({stop_pct*100:.1f}%)"

        if exit_triggered:
            pnl = (current_value - entry_value) if position_dir == "long" else (entry_value - current_value)
            trades.append({
                "entry_date": entry_date,
                "entry_value": entry_value,
                "entry_signal": entry_signal,
                "exit_date": date,
                "exit_value": current_value,
                "exit_reason": exit_reason,
                "pnl": pnl,
                "direction": position_dir,
                "holding_days": days_in_trade,
            })
            in_position = False
            entry_date = None
            entry_value = None
            entry_signal = None
            days_in_trade = 0

    # If still in position at end of data, close it out
    if in_position and entry_date is not None:
        final_date = comparator_series.index[-1]
        final_value = get_position_value(position_cfg, signal_cfg, final_date)
        pnl = (final_value - entry_value) if position_dir == "long" else (entry_value - final_value)
        trades.append({
            "entry_date": entry_date,
            "entry_value": entry_value,
            "entry_signal": entry_signal,
            "exit_date": final_date,
            "exit_value": final_value,
            "exit_reason": "End of data",
            "pnl": pnl,
            "direction": position_dir,
            "holding_days": days_in_trade,
        })

    # ============================================================
    # 4. Compute aggregate statistics
    # ============================================================
    stats = _compute_stats(trades)

    # ============================================================
    # 5. Build equity curve
    # ============================================================
    equity_curve = _build_equity_curve(trades, comparator_series.index[0], comparator_series.index[-1])

    return {
        "ok": True,
        "trades": trades,
        "stats": stats,
        "equity_curve": equity_curve,
        "signal_series": comparator_series,
        "raw_signal_series": signal_series,
        "threshold": threshold,
        "strategy_name": strategy.get("name", "Unnamed Strategy"),
    }


def _compute_stats(trades: list) -> dict:
    """Compute aggregate stats from trade list."""
    if not trades:
        return {
            "num_trades": 0,
            "win_rate": 0.0,
            "avg_pnl": 0.0,
            "total_pnl": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "avg_holding_days": 0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
        }

    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    holding = [t["holding_days"] for t in trades]

    total_pnl = sum(pnls)
    avg_pnl = total_pnl / len(pnls)
    std_pnl = float(np.std(pnls, ddof=1)) if len(pnls) > 1 else 0.0
    sharpe = (avg_pnl / std_pnl) * np.sqrt(252 / max(1, np.mean(holding))) if std_pnl > 0 else 0.0

    # Drawdown
    cum = np.cumsum(pnls)
    running_max = np.maximum.accumulate(cum)
    drawdowns = running_max - cum
    max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

    return {
        "num_trades": len(trades),
        "win_rate": len(wins) / len(pnls) if pnls else 0.0,
        "avg_pnl": avg_pnl,
        "total_pnl": total_pnl,
        "best_trade": max(pnls),
        "worst_trade": min(pnls),
        "avg_holding_days": int(np.mean(holding)) if holding else 0,
        "sharpe": float(sharpe),
        "max_drawdown": max_dd,
    }


def _build_equity_curve(trades: list, start_date, end_date) -> list:
    """Build a cumulative PnL series across the backtest period."""
    if not trades:
        return []

    # Sort by exit date
    sorted_trades = sorted(trades, key=lambda t: t["exit_date"])
    cumulative = 0.0
    curve = [(start_date, 0.0)]
    for t in sorted_trades:
        cumulative += t["pnl"]
        curve.append((t["exit_date"], cumulative))
    curve.append((end_date, cumulative))
    return curve


def _empty_result(reason: str) -> dict:
    return {
        "ok": False,
        "reason": reason,
        "trades": [],
        "stats": _compute_stats([]),
        "equity_curve": [],
        "signal_series": pd.Series(dtype=float),
        "raw_signal_series": pd.Series(dtype=float),
    }


# ============================================================
# CONVENIENCE: PRESET STRATEGIES (for testing)
# ============================================================

PRESET_STRATEGIES = {
    "brent_m1_m2_mean_revert": {
        "name": "Brent M1-M2 Mean Reversion",
        "signal": {
            "type": "z_score",
            "instrument": "Brent",
            "metric": "spread_M1_M2",
            "lookback_days": 252,
            "entry_threshold": 2.0,
            "entry_direction": "above",
        },
        "position": {
            "structure": "calendar_spread",
            "direction": "short",
        },
        "exit": {
            "rules": ["mean_revert", "time_stop"],
            "time_stop_days": 20,
        },
        "lookback_years": 5,
    },
    "wti_steep_contango": {
        "name": "WTI Steep Contango",
        "signal": {
            "type": "curve_shape",
            "instrument": "WTI",
            "metric": "front_to_M12_pct",
            "lookback_days": 252,
            "entry_threshold": -8.0,  # negative because contango means M1 < M12
            "entry_direction": "below",
        },
        "position": {
            "structure": "calendar_spread",
            "direction": "long",  # buy front, sell back when curve is too contango
        },
        "exit": {
            "rules": ["mean_revert", "time_stop"],
            "time_stop_days": 30,
        },
        "lookback_years": 5,
    },
    "brent_oversold_revert": {
        "name": "Brent Oversold Mean Reversion",
        "signal": {
            "type": "price",
            "instrument": "Brent",
            "metric": "front_vs_ma_60",
            "lookback_days": 252,
            "entry_threshold": -10.0,  # 10% below 60-day MA
            "entry_direction": "below",
        },
        "position": {
            "structure": "outright",
            "direction": "long",
        },
        "exit": {
            "rules": ["mean_revert", "time_stop"],
            "time_stop_days": 30,
        },
        "lookback_years": 5,
    },
}