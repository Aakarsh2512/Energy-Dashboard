# Energy & Oil Trading Dashboard

A research and monitoring dashboard for an energy and oil trading desk, built in Python
and Streamlit. It pulls settlement and live pricing for WTI, Brent, gasoil, ULSD and
Henry Hub, layers analytics on top — HMM regime classification, shock detection,
spread and fly construction, seasonality, support and resistance — and lets you build,
backtest and journal rule-based strategies against real settlement history.

Built by Aakarsh Varshney.

<!-- Add a screenshot once you have one: ![Dashboard](docs/screenshot.png) -->

---

## The dashboard

Seven tabs, each backed by its own module:

| Tab | What it does |
|---|---|
| **Markets** | Live price grid for WTI, Brent, Henry Hub and products, macro panel, forward curves |
| **Inventory** | Weekly EIA inventory releases and European storage, against expectation and season |
| **Seasonality** | Year-on-year and rebased seasonal behaviour by contract |
| **News & Events** | Headline feed with LLM tagging, behind a feature flag |
| **Spreads, Flies & Correlations** | Calendar spreads, butterflies and a cross-product correlation matrix |
| **★ Strategy Lab** | Configure a rule-based strategy, backtest it on settlement history, save, reload and A/B compare; win rate and P&L tracking |
| **★ Replay** | Step the dashboard through history to see what the desk would have seen on a given day, with alerts replayed alongside |

The header strip refreshes on a 60-second timer.

---

## Analytics

### Regime classification — `src/regime_classifier.py`

A five-state Gaussian HMM (`hmmlearn`, full covariance) fitted over standardised features
from the feature store. It labels every trading day with a market regime, persists the
fitted model and scaler, and writes labels and per-regime metadata back to the data
directory for the rest of the dashboard to consume.

### Shock detection — `src/shock_detector.py`

Flags abnormal moves relative to the prevailing regime and aggregates them, so a shock is
judged against what the market was actually doing at the time rather than one global
threshold.

### Feature store — `src/feature_engine.py`

Builds the master feature table from the settlement series and writes it to parquet, so
the classifier and the dashboard read one consistent set of features instead of each
recomputing its own.

### Strategy Lab — `src/strategy_engine.py`, `src/strategy_store.py`

A rule-based backtester over real settlement history. Strategies are configured in the
UI, run through `run_backtest`, and scored on win rate, total P&L and profit factor.
Saved strategies persist, and two can be loaded and compared side by side.

### Market structure

`spreads_flies.py`, `correlations.py`, `seasonality.py`, `support_resistance.py` and
`forward_curves.py` cover calendar spreads and butterflies, cross-product correlation,
seasonal decomposition, level detection and curve construction. Each is usable standalone
or through the dashboard.

---

## Results

| Metric | Value |
|---|---|
| Strategy backtest — profit factor | 1.47 over 82 trades |
| Live journal — profit factor | 6.85, 64.3% win rate |
| EIA-release reaction model — directional accuracy | 4 / 4 releases |
| EIA-release reaction model — hit rate | up to 78.4% |
| EIA-release reaction model — R² | 0.988 |

**Read these with their sample sizes attached.** 4/4 is four observations, and the live
journal covers a short window. The 82-trade backtest is the most meaningful number here.

> **On the forecasting model.** The three-stage ensemble behind the EIA-release numbers
> (Random Forest, Logistic Regression, Ridge, Gradient Boosting) was developed in
> notebooks and is **not yet in this repository** — what ships here is the dashboard, the
> HMM regime engine and the strategy backtester. Adding the notebook under `notebooks/`
> would let a reader reproduce those figures.

---

## Setup

Requires Python 3.10+.

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1        # Windows
source venv/bin/activate           # macOS / Linux

pip install -r requirements.txt
streamlit run src/app.py
```

### API keys

Create a `.env` in the project root. It is gitignored and must never be committed.

```
EIA_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
ENABLE_NEWS_TAGGING=false
```

| Key | Used for | Where |
|---|---|---|
| `EIA_API_KEY` | weekly US inventory data | `src/eia_data.py` |
| `GEMINI_API_KEY` | LLM tagging of headlines | `src/news_worker.py` |
| `GROQ_API_KEY` | currently unused, left over from an earlier news pipeline | - |
| `ENABLE_NEWS_TAGGING` | feature flag, defaults to `false` | `src/news_worker.py` |

The dashboard runs without the news keys; tagging simply stays off.

### Data

`data/` is gitignored — settlement CSVs, the parquet feature store and the fitted HMM are
pipeline outputs, not source. Rebuild them by running the ingestion and feature modules
(`settle_data.py`, then `feature_engine.py`, then `regime_classifier.py`) before
launching the dashboard.

---

## Layout

```
src/
  app.py                  Streamlit entry point, tab wiring
  components.py           tab rendering
  styles/                 dark theme and custom CSS

  settle_data.py          settlement price ingestion
  brent_data.py           Brent series
  convert_intraday_to_daily.py
  market_data.py          live pricing
  eia_data.py             EIA weekly inventories
  european_storage.py     European storage
  forward_curves.py       forward curve construction
  news_data.py            headline feed
  news_worker.py          background LLM tagging

  feature_engine.py       master feature store
  regime_classifier.py    5-state Gaussian HMM
  shock_detector.py       regime-relative shock flagging
  correlations.py         cross-product correlation
  spreads_flies.py        calendar spreads and butterflies
  seasonality.py          seasonal analysis
  support_resistance.py   level detection

  strategy_engine.py      rule-based backtester
  strategy_store.py       strategy persistence
  alerts.py               alerting
  replay_data.py          historical replay
  replay_alerts.py        alerts during replay

data/                     pipeline outputs (gitignored)
```

---

## Stack

Python, Streamlit, Plotly, pandas, NumPy, scikit-learn, hmmlearn, yfinance, feedparser.
