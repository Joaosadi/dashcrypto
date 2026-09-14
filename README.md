# DashCrypto

A **Quantitative Crypto Market Dashboard** built with Streamlit and Altair — technical indicators, statistical models, and macro analysis for Bitcoin and the broader crypto market.

Live metrics (BTC price, market cap, BTC dominance, stablecoin prices) sit on top of deep historical analysis across three tabs: **BTC Price Metrics**, **Stablecoins**, and **Macro Metrics**.

---

## Features

| Tab | What it shows |
| --- | --- |
| Header metrics | Live Bitcoin price, total crypto market cap, 24h volume, BTC dominance, USDT/USDC prices (CoinGecko, 5-min cache) |
| BTC Price Metrics | Log-polynomial regression fit + rainbow bands, drawdown-from-regression, N-year rolling returns with Student's t-distribution fit, realized volatility and Relative Volatility Index (RVI) |
| Stablecoins | Circulating supply (absolute $ or % share), DeFi Llama chain distribution, per-stablecoin dominance, and price-peg histograms |
| Macro Metrics | FRED indicators (DXY, 10Y Treasury yield, Fed balance sheet, yield curve slope) merged with BTC price, weekly resampled dual-axis charts |

The dashboard is fully responsive — charts stack into full-width cards on phones via CSS media queries, and every Altair chart renders at container width.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
streamlit run app.py
```

Open http://localhost:8501. The app reads historical data from the bundled SQLite database (`crypto_historical_data.db`) and fetches live snapshots from CoinGecko.

### Dev container

A pre-configured devcontainer is included — it installs `requirements.txt`, launches the app on port `8501` with preview auto-forwarding, and works in GitHub Codespaces or VS Code Dev Containers.

---

## Architecture

```
Data Sources          Processing           Visualization        Delivery
─────────────        ──────────           ─────────────        ────────
Binance API    ──►  btcdatagathering  ──►  plots/            ──►  app.py
CoinGecko API  ──►  marketsnapshot    ──►  (Altair charts)   ──►  Streamlit
DeFi Llama     ──►  defillammastable  ──►                    ──►  Dashboard
FRED           ──►  macrodata         ──►
CSV files      ──►  tablefixing       ──►
                        │
                        ▼
              crypto_historical_data.db
                   (SQLite)
```

---

## Project Structure

```
app.py                          Streamlit dashboard entry point
style.css                       Custom CSS (dark theme, responsive media queries)
.streamlit/config.toml          Streamlit dark theme configuration
plots/
  btcregressionplots.py         Log regression, rainbow bands, drawdown plots
  btcreturns.py                 Rolling returns + t-distribution fitting
  btcvolatilityplots.py         Realized volatility, RVI
  stablecoinsplot.py            Stablecoin supply, dominance, peg histograms
  macroplots.py                 Macro indicators vs BTC (FRED)
  metrics.py                    CoinGecko snapshot helpers (5-min cache)
*.ipynb                         One-off data pipeline notebooks
crypto_historical_data.db       SQLite database (BTC OHLCV + macro data)
CHANGELOG.md                    Release history (git-cliff generated)
cliff.toml                      git-cliff changelog configuration
```

## Data Pipelines

| Notebook / Script | Purpose |
| --- | --- |
| `btcdatagathering.ipynb` | Fetches daily BTC/USDT candles from the Binance REST API with delta updates into `crypto_historical_data.db` |
| `btcpriceupdate.py` | Standalone BTC price DB updater, built for cron/scheduled execution (see `.github/workflows/daily_btc_price_update.yml`) |
| `tablefixing.ipynb` | Merges and deduplicates BTC price data from legacy sources into a clean `btc_price` table |
| `datamodeling.ipynb` | Log-polynomial regression fit of BTC close prices (`scipy.optimize.curve_fit`) |
| `defillammastablecoins.ipynb` | Stablecoin market data from the DeFi Llama API (circulating supply, chain distribution, price histograms) |
| `macrodata.ipynb` | Pulls FRED macro indicators and merges them with BTC price |
| `marketsnapshot.ipynb` | Real-time market metrics via CoinGecko |

## Data Coverage

| Dataset | Source | Range | Granularity |
| --- | --- | --- | --- |
| BTC OHLCV | Binance | Jul 2010 – Present | Daily |
| Stablecoin Circulating Supply | DeFi Llama | Dec 2017 – Present | Weekly |
| Stablecoin Prices | DeFi Llama | 2017 – Present | Daily |
| DXY, 10Y Yield, Fed Balance Sheet | FRED | Jan 2006 – Present | Daily |
| Global Market Cap / BTC Dominance | CoinGecko | Real-time | On-demand |

---

## Tech Stack

- [Streamlit](https://streamlit.io) ≥ 1.49 — app framework
- [Altair](https://altair-viz.github.io) ≥ 5 — declarative charts
- [pandas](https://pandas.pydata.org) / [numpy](https://numpy.org) — data handling
- [scipy](https://scipy.org) — curve fitting and statistical models
- [pandas-datareader](https://pydata.github.io/pandas-datareader/) — FRED economic data
- APIs: Binance, CoinGecko, DeFi Llama

## Development

The changelog is generated with [git-cliff](https://git-cliff.org) from conventional commits, and auto-updated by CI. To stamp a new release manually:

```bash
git cliff --tag 0.2.0 -o CHANGELOG.md
```

Automated workflows in `.github/workflows/` keep the changelog fresh and update daily BTC candles on schedule.