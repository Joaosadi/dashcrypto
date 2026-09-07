---
tags:
  - index
  - crypto
  - dashboard
aliases:
  - Dashboard Index
---

# DashCrypto - Project Index

A **Quantitative Crypto Market Dashboard** built with Streamlit and Altair, providing technical indicators, statistical models, and macro analysis for Bitcoin and the broader crypto market.

---

## Application

- [[app.py]] — Main Streamlit dashboard entry point. Loads data from SQLite, displays real-time metrics (BTC price, market cap, dominance, stablecoin prices), and organizes analysis into three tabs: BTC Price Metrics, Stablecoins, and Macro Metrics.

## Data Pipeline

- [[btcdatagathering]] — Fetches daily BTC/USDT candlestick data from the Binance REST API and performs delta updates into `crypto_historical_data.db`.
- [[btcpriceupdate]] — Standalone script for automated BTC price database updates (intended for cron/scheduled execution).
- [[tablefixing]] — Merges and deduplicates BTC price data from an old database (`crypto_historical_data_old.db`), a Binance CSV export, and the new database to create a clean, unified `btc_price` table (2010-present, ~5,859 daily candles).

## Data Modeling & Statistical Analysis

- [[datamodeling]] — Log-polynomial regression model ($p_1 + p_2 \ln(x) + p_3 \ln^2(x)$) fitted to BTC daily close prices using `scipy.optimize.curve_fit`. Serves as the foundation for rainbow chart and regression bands.

## Stablecoin Analytics

- [[defillammastablecoins]] — Fetches stablecoin market data from the DeFi Llama API (circulating supply, historical prices, chain distribution, price histograms). Generates market dominance charts, historical stacked area plots, and cross-chain stablecoin distribution visualizations.

## Macro Economics

- [[macrodata]] — Pulls FRED macro indicators (DXY, 10Y yield, Fed balance sheet, yield curve slope) and merges them with BTC price. Includes ML feature engineering (`generate_macro_ml_features`) for rate-of-change, momentum, and regime detection.

## Market Snapshot

- [[marketsnapshot]] — Real-time market metrics via CoinGecko API: total crypto market cap, 24h volume, BTC dominance, and live prices for BTC, USDT, and USDC.

---

## Visualization Modules (`plots/`)

- [[plots/btcregressionplots]] — Log regression curves, rainbow regression bands, and BTC drawdown-from-regression plots using Altair.
- [[plots/btcreturns]] — N-year rolling returns distribution and Student's t-distribution fitting for BTC returns.
- [[plots/btcvolatilityplots]] — Realized volatility, Relative Volatility Index (RVI), and Bollinger-style volatility bands.
- [[plots/stablecoinsplot]] — Stablecoin historical circulating supply (stacked area), market dominance (pie chart), chain distribution, and price peg histograms.
- [[plots/macroplots]] — Interactive dual-axis Altair charts for macro indicators vs BTC price.
- [[plots/metrics]] — Real-time metric fetching helpers (CoinGecko snapshot + global market metrics).

## Styling

- [[style.css]] — Custom CSS for the Streamlit dashboard (title banner, dark theme, footer).

## Dependencies

- [[requirements.txt]] — `streamlit`, `pandas`, `numpy`, `scipy`, `altair`

## Infrastructure

- [[CHANGELOG.md]] — Version history (currently empty)
- [[cliff.toml]] — Configuration for `git-cliff` changelog generator

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

## Data Coverage

| Dataset | Source | Range | Granularity |
| --- | --- | --- | --- |
| BTC OHLCV | Binance | Jul 2010 – Present | Daily |
| Stablecoin Circulating | DeFi Llama | Dec 2017 – Present | Weekly |
| Stablecoin Prices | DeFi Llama | 2017 – Present | Daily |
| DXY, 10Y Yield, Fed BS | FRED | Jan 2006 – Present | Daily |
| Global Market Cap | CoinGecko | Real-time | On-demand |
