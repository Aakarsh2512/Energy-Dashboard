"""
HMM-based Regime Classifier.

Fits a Gaussian Hidden Markov Model on the master features table to classify
every historical day into one of N market regimes. Regimes are persistent
(transition matrix has strong diagonal), interpretable (each has a clear
fingerprint), and probabilistic (predict_proba returns full state vector).

Outputs:
    data/regime_labels.parquet     — date × regime label, probabilities
    data/hmm_model.pkl             — fitted hmmlearn GaussianHMM
    data/regime_metadata.json      — regime names, fingerprints, transition matrix

Used downstream by:
    regression_engine.py (per-regime regressions)
    opportunity_ranker.py (regime-conditional signals)
"""

import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler
from feature_engine import load_master_features

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

LABELS_PATH = DATA_DIR / "regime_labels.parquet"
MODEL_PATH = DATA_DIR / "hmm_model.pkl"
META_PATH = DATA_DIR / "regime_metadata.json"


# ============================================================
# 1. FEATURE SELECTION FOR HMM
# ============================================================

def select_hmm_features(master: pd.DataFrame) -> pd.DataFrame:
    """..."""
    feature_cols = [
        # Curve state (Brent — 10-year history)
        "brent_vol_20d",
        "brent_front_to_m12_pct",
        "brent_curve_slope",
        "brent_front_fly",

        # Macro state
        "dxy_level",
        "vix_level",
        "spx_mom_20d",
        "copper_mom_20d",
    ]

    # Verify all columns exist
    missing = [c for c in feature_cols if c not in master.columns]
    if missing:
        raise RuntimeError(f"Missing feature columns: {missing}")

    return master[feature_cols].copy()


# ============================================================
# 2. FIT THE HMM
# ============================================================

def fit_hmm(
    n_states: int = 5,
    random_state: int = 42,
    n_iter: int = 200,
    covariance_type: str = "full",
):
    """
    Fit a Gaussian HMM on the master features.

    Args:
        n_states: number of regimes (typically 4-6 for financial data)
        random_state: for reproducibility
        n_iter: max EM iterations
        covariance_type: 'full' (most flexible) or 'diag' (more stable, less expressive)

    Returns:
        dict with model, scaler, labels DataFrame, metadata
    """
    print("\n" + "=" * 60)
    print(f"Fitting HMM Regime Classifier (n_states={n_states})")
    print("=" * 60)

    # Load features
    print("\n[1/5] Loading master features...")
    master = load_master_features()
    feats = select_hmm_features(master)
    print(f"  Selected {feats.shape[1]} features × {feats.shape[0]} days")

    # Drop rows with any NaN (HMM cannot handle missing values)
    feats_clean = feats.dropna()
    n_dropped = len(feats) - len(feats_clean)
    print(f"  Dropped {n_dropped} rows with NaN (mostly early dates with rolling-vol burn-in)")
    print(f"  Final fit set: {feats_clean.shape}")

    if len(feats_clean) < 200:
        raise RuntimeError("Not enough clean rows to fit HMM reliably")

    # Standardize features (HMM with Gaussian emissions benefits from this)
    print("\n[2/5] Standardizing features (z-score)...")
    scaler = StandardScaler()
    X = scaler.fit_transform(feats_clean.values)

    # Fit HMM
    print(f"\n[3/5] Fitting GaussianHMM with {covariance_type} covariance...")
    print(f"  EM iterations capped at {n_iter}")
    model = GaussianHMM(
        n_components=n_states,
        covariance_type=covariance_type,
        n_iter=n_iter,
        tol=1e-3,
        random_state=random_state,
        verbose=False,
    )
    model.fit(X)

    print(f"  Converged: {model.monitor_.converged}")
    print(f"  Final log-likelihood: {model.monitor_.history[-1]:.2f}")

    # Decode most likely state sequence (Viterbi)
    print("\n[4/5] Decoding most likely regime sequence (Viterbi)...")
    states = model.predict(X)
    probs = model.predict_proba(X)

    # Build labels DataFrame
    labels = pd.DataFrame(
        {"regime": states},
        index=feats_clean.index,
    )
    for i in range(n_states):
        labels[f"prob_regime_{i}"] = probs[:, i]

    # Compute regime metadata
    print("\n[5/5] Computing regime metadata (fingerprints + transitions)...")
    metadata = compute_regime_metadata(
        model=model,
        scaler=scaler,
        features_clean=feats_clean,
        labels=labels,
        feature_names=feats.columns.tolist(),
    )

    print(f"\n  Regime durations (median days in state):")
    for i, dur in enumerate(metadata["median_durations"]):
        print(f"    Regime {i}: {dur:.1f} days · "
              f"{metadata['frequencies'][i]*100:.1f}% of history · "
              f"\"{metadata['regime_names'][i]}\"")

    print(f"\n  Transition matrix (diagonal = stickiness):")
    diag = np.diag(metadata["transition_matrix"])
    for i, d in enumerate(diag):
        print(f"    Regime {i} → stays {d*100:.1f}% of days")

    return {
        "model": model,
        "scaler": scaler,
        "feature_names": feats.columns.tolist(),
        "labels": labels,
        "metadata": metadata,
    }


# ============================================================
# 3. REGIME METADATA — fingerprints, transitions, names
# ============================================================

def compute_regime_metadata(
    model: GaussianHMM,
    scaler: StandardScaler,
    features_clean: pd.DataFrame,
    labels: pd.DataFrame,
    feature_names: list,
) -> dict:
    """Compute interpretability metadata for each regime."""
    n_states = model.n_components

    # Mean of each feature within each regime (in original units, not z-scored)
    fingerprints = []
    for i in range(n_states):
        mask = labels["regime"] == i
        if mask.sum() == 0:
            fingerprints.append({name: float("nan") for name in feature_names})
            continue
        regime_data = features_clean[mask]
        fingerprints.append({
            name: float(regime_data[name].mean())
            for name in feature_names
        })

    # Regime frequencies
    counts = labels["regime"].value_counts().sort_index()
    frequencies = [counts.get(i, 0) / len(labels) for i in range(n_states)]

    # Median duration per regime: find consecutive runs, take median length
    median_durations = []
    for i in range(n_states):
        runs = _find_runs(labels["regime"].values, target=i)
        median_durations.append(float(np.median(runs)) if runs else 0.0)

    # Transition matrix (already in the model)
    transition_matrix = model.transmat_.tolist()

    # Auto-name regimes based on feature fingerprints
    regime_names = _name_regimes_automatically(fingerprints, feature_names)

    return {
        "n_states": n_states,
        "feature_names": feature_names,
        "fingerprints": fingerprints,
        "frequencies": frequencies,
        "median_durations": median_durations,
        "transition_matrix": transition_matrix,
        "regime_names": regime_names,
    }


def _find_runs(arr, target):
    """Return list of run lengths where arr == target."""
    runs = []
    current = 0
    for x in arr:
        if x == target:
            current += 1
        else:
            if current > 0:
                runs.append(current)
            current = 0
    if current > 0:
        runs.append(current)
    return runs


def _name_regimes_automatically(fingerprints: list, feature_names: list) -> list:
    """
    Heuristically name each regime by inspecting its fingerprint relative to
    the cross-regime averages.

    Each regime gets a 2-3 word label combining:
        - Vol level: "Low Vol" / "Normal Vol" / "High Vol"
        - Curve shape: "Backwardation" / "Contango" / "Flat"
        - Macro context: "Risk-On" / "Risk-Off" (from VIX + SPX)
    """
    if not fingerprints:
        return []

    # Compute cross-regime averages
    all_vol = [fp.get("brent_vol_20d", np.nan) for fp in fingerprints]
    all_curve = [fp.get("brent_front_to_m12_pct", np.nan) for fp in fingerprints]
    all_vix = [fp.get("vix_level", np.nan) for fp in fingerprints]

    vol_median = np.nanmedian(all_vol) if all_vol else 0
    curve_median = np.nanmedian(all_curve) if all_curve else 0
    vix_median = np.nanmedian(all_vix) if all_vix else 0

    names = []
    for fp in fingerprints:
        vol = fp.get("brent_vol_20d", vol_median)
        curve = fp.get("brent_front_to_m12_pct", curve_median)
        vix = fp.get("vix_level", vix_median)

        # Vol descriptor
        if vol > vol_median * 1.3:
            vol_lbl = "High Vol"
        elif vol < vol_median * 0.7:
            vol_lbl = "Low Vol"
        else:
            vol_lbl = "Normal Vol"

        # Curve descriptor
        if curve > 3:
            curve_lbl = "Backwardation"
        elif curve < -3:
            curve_lbl = "Contango"
        else:
            curve_lbl = "Flat Curve"

        # Risk context
        if vix > vix_median * 1.3:
            risk_lbl = "Risk-Off"
        elif vix < vix_median * 0.7:
            risk_lbl = "Risk-On"
        else:
            risk_lbl = ""

        parts = [vol_lbl, curve_lbl]
        if risk_lbl:
            parts.append(risk_lbl)
        names.append(" · ".join(parts))

    return names


# ============================================================
# 4. SAVE / LOAD
# ============================================================

def save_artifacts(result: dict):
    """Persist the fitted model, labels, and metadata to disk."""
    DATA_DIR.mkdir(exist_ok=True)

    # Model + scaler in pickle
    with open(MODEL_PATH, "wb") as f:
        pickle.dump({
            "model": result["model"],
            "scaler": result["scaler"],
            "feature_names": result["feature_names"],
        }, f)
    print(f"  Saved model to {MODEL_PATH}")

    # Labels as parquet
    result["labels"].to_parquet(LABELS_PATH)
    print(f"  Saved labels to {LABELS_PATH}")

    # Metadata as JSON
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(result["metadata"], f, indent=2, default=str)
    print(f"  Saved metadata to {META_PATH}")


def load_artifacts() -> dict:
    """Load the saved HMM, labels, and metadata."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"{MODEL_PATH} not found. Run regime_classifier.py first.")

    with open(MODEL_PATH, "rb") as f:
        model_bundle = pickle.load(f)

    labels = pd.read_parquet(LABELS_PATH)
    with open(META_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    return {
        "model": model_bundle["model"],
        "scaler": model_bundle["scaler"],
        "feature_names": model_bundle["feature_names"],
        "labels": labels,
        "metadata": metadata,
    }


# ============================================================
# 5. PREDICT CURRENT REGIME
# ============================================================

def classify_current_regime() -> dict:
    """
    Identify the current regime by applying the fitted HMM to today's features.
    Returns full diagnostic dict.
    """
    artifacts = load_artifacts()
    labels = artifacts["labels"]
    metadata = artifacts["metadata"]

    # The latest day in the labels table = today's classification
    latest_date = labels.index[-1]
    latest_label = int(labels.loc[latest_date, "regime"])

    probs = [
        float(labels.loc[latest_date, f"prob_regime_{i}"])
        for i in range(metadata["n_states"])
    ]

    # How long have we been in this regime?
    days_in_current = _days_in_current_regime(labels)

    return {
        "regime_id": latest_label,
        "regime_name": metadata["regime_names"][latest_label],
        "date": latest_date,
        "probabilities": probs,
        "days_in_current_regime": days_in_current,
        "median_duration_for_this_regime": metadata["median_durations"][latest_label],
        "all_regime_names": metadata["regime_names"],
        "all_fingerprints": metadata["fingerprints"],
        "transition_matrix": metadata["transition_matrix"],
    }


def _days_in_current_regime(labels: pd.DataFrame) -> int:
    """Count consecutive days at the end with same regime label as the last day."""
    current = labels["regime"].iloc[-1]
    count = 0
    for r in reversed(labels["regime"].values):
        if r == current:
            count += 1
        else:
            break
    return count


# ============================================================
# CLI ENTRY POINT
# ============================================================

if __name__ == "__main__":
    result = fit_hmm(n_states=5)
    save_artifacts(result)

    print("\n" + "=" * 60)
    print("HMM fit complete. Current regime:")
    print("=" * 60)
    current = classify_current_regime()
    print(f"\n  Date: {current['date'].strftime('%d %b %Y')}")
    print(f"  Regime: {current['regime_id']} — \"{current['regime_name']}\"")
    print(f"  Days in this regime: {current['days_in_current_regime']}")
    print(f"  Median historical duration: {current['median_duration_for_this_regime']:.1f} days")
    print(f"\n  Probability distribution:")
    for i, (name, p) in enumerate(zip(current["all_regime_names"], current["probabilities"])):
        bar = "█" * int(p * 40)
        print(f"    [{i}] {name:50s} {p*100:5.1f}% {bar}")