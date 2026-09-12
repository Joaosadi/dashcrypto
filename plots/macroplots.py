import datetime

import altair as alt
import pandas as pd
import streamlit as st
import pandas_datareader.data as web

# Default Global Setup (mirrors the BTC price metrics charts)
alt.data_transformers.disable_max_rows()
alt.themes.enable("dark")

def merge_btc_with_macro(btc_df, macro):
    macro = macro.copy()
    macro.index = pd.to_datetime(macro.index, utc=False).tz_localize(None).normalize()
    macro.index.name = "date"
    
    btc = btc_df.copy()
    btc["date"] = (
        pd.to_datetime(btc["time_close"], utc=True, format="mixed")
        .dt.tz_convert("UTC")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    btc = (
        btc.rename(columns={"close": "btc_close"})
        .groupby("date", as_index=True)[["btc_close"]]
        .last()
        .sort_index()
    )
    
    merged = macro.join(btc, how="inner")
    return merged


def fetch_fred_macro_data(start_date="2006-01-01", end_date=None):
    """Fetches macro data series from FRED without needing an API key.

    Series:
    - DTWEXBGS: US Dollar Index (Nominal Broad Dollar Index)
    - DGS10: 10-Year Treasury Constant Maturity Rate
    - WALCL: Federal Reserve Total Assets (Fed Balance Sheet)
    - T10Y2Y: 10-Year Treasury Constant Maturity Minus 2-Year Constant Maturity
    """
    if end_date is None:
        end_date = datetime.datetime.now().strftime("%Y-%m-%d")

    series_mapping = {
        "DTWEXBGS": "dxy",
        "DGS10": "us_10y_yield",
        "WALCL": "fed_balance_sheet",
        "T10Y2Y": "yield_curve_slope",
    }

    tickers = list(series_mapping.keys())

    try:
        # Pull data directly from FRED
        df_raw = web.DataReader(tickers, "fred", start_date, end_date)
        df = df_raw.rename(columns=series_mapping)
    except Exception as e:
        st.write(f"Error fetching data from FRED: {e}")
        return pd.DataFrame()

    # Create daily calendar grid to handle weekend/holiday gaps & low-frequency metrics
    full_idx = pd.date_range(start=start_date, end=end_date, freq="D")
    df = df.reindex(full_idx)

    # Forward-fill macro data (Fed Balance sheet is weekly, markets close on weekends)
    df = df.ffill().bfill()

    return df


def generate_macro_ml_features(df):
    """Generates rate-of-change, momentum, and regime features for ML training."""
    features = pd.DataFrame(index=df.index)

    # 1. Dollar Index (DXY) Momentum (14-day and 30-day % changes)
    features["dxy_roc_14d"] = df["dxy"].pct_change(14)
    features["dxy_roc_30d"] = df["dxy"].pct_change(30)

    # 2. Yield Curve slope momentum & Z-score (Inversion indicator)
    features["yield_curve_slope"] = df["yield_curve_slope"]
    rolling_mean = df["yield_curve_slope"].rolling(90).mean()
    rolling_std = df["yield_curve_slope"].rolling(90).std()
    features["yield_curve_zscore_90d"] = (
        df["yield_curve_slope"] - rolling_mean
    ) / rolling_std

    # 3. Fed Balance Sheet Velocity (Global Liquidity Proxy)
    # WALCL is reported in millions, calculate 30-day % expansion/contraction
    features["fed_bs_expansion_30d"] = df["fed_balance_sheet"].pct_change(30)

    # 4. Macro Risk-On/Off Compound Score
    # Dollar strength + rising yields = liquidity contraction (Risk-Off)
    features["liquidity_stress_index"] = (
        features["dxy_roc_14d"] + df["us_10y_yield"].pct_change(14)
    )

    return features.dropna()


# charts


indicator_meta = {
    "dxy": {
        "title": "US Dollar Index (Nominal Broad, DTWEXBGS)",
        "ylabel": "Index",
        "legend": "Dollar Index (DXY)",
    },
    "us_10y_yield": {
        "title": "10-Year Treasury Yield (DGS10)",
        "ylabel": "Percent",
        "legend": "10-Year Yield",
    },
    "fed_balance_sheet": {
        "title": "Fed Total Assets (WALCL)",
        "ylabel": "USD millions",
        "legend": "Fed Balance Sheet",
    },
    "yield_curve_slope": {
        "title": "10Y–2Y Yield Curve Slope (T10Y2Y)",
        "ylabel": "Percentage points",
        "legend": "10Y-2Y Slope",
    },
}



def create_indicator_chart(df, col, meta=None):
    """Generates a responsive dual-axis Altair chart optimized for mobile screens."""
    if meta is None:
        meta = indicator_meta[col]

    # Ensure date is a column with proper datetime dtype
    data = df.copy()
    if isinstance(data.index, pd.DatetimeIndex) or data.index.name == "date":
        data = data.reset_index()

    # Normalize date column name
    date_col = "index" if "index" in data.columns else "date"
    data[date_col] = pd.to_datetime(data[date_col])

    # 0. Master Legend Scale (Posicionada na parte inferior para economizar espaço horizontal)
    color_scale = alt.Color(
        "legend:N",
        scale=alt.Scale(
            domain=["BTC Price", meta["legend"]],
            range=["#7FFFD4", "#1E90FF"],  # Aquamarine & Dodger Blue
        ),
        legend=alt.Legend(
            title=None,
            orient="bottom",  # Move a legenda para baixo
            direction="horizontal",
            fillColor="#0e1117",
            strokeColor="#333333",
            padding=5,
            cornerRadius=5,
            labelColor="#cccccc",
            labelFontSize=11,
        ),
    )

    # 1. Base x-axis configuration
    base = alt.Chart(data).encode(
        x=alt.X(
            f"{date_col}:T",
            title=None,  # Remove o título "Date" para poupar espaço vertical
            axis=alt.Axis(
                format="%Y-%m",
                gridColor="#222222",
                labelColor="#cccccc",
                labelAngle=-45,  # Inclina os rótulos de data no mobile
                labelFontSize=10,
            ),
        )
    )

    # 2. Primary Y-Axis: Macro Indicator (Left Axis)
    macro_line = base.mark_line(strokeWidth=1.5).encode(
        y=alt.Y(
            f"{col}:Q",
            title=meta["ylabel"],
            scale=alt.Scale(zero=False),
            axis=alt.Axis(
                titleColor="#1E90FF",
                labelColor="#cccccc",
                gridColor="#222222",
                labelFontSize=10,
                titleFontSize=11,
            ),
        ),
        color=color_scale,
        tooltip=[
            alt.Tooltip(f"{date_col}:T", title="Date", format="%Y-%m-%d"),
            alt.Tooltip(f"{col}:Q", title=meta["title"], format=".2f"),
        ],
    ).transform_calculate(legend=f"'{meta['legend']}'")

    # 3. Secondary Y-Axis: BTC Close (Right Axis, Log Scale)
    btc_line = base.mark_line(
        strokeWidth=1.5, opacity=0.85
    ).encode(
        y=alt.Y(
            "btc_close:Q",
            title="BTC (Log)",  # Encurtado para caber em telas pequenas
            scale=alt.Scale(type="log"),
            axis=alt.Axis(
                titleColor="#7FFFD4",
                labelColor="#cccccc",
                orient="right",
                labelFontSize=10,
                titleFontSize=11,
            ),
        ),
        color=color_scale,
        tooltip=[
            alt.Tooltip(f"{date_col}:T", title="Date", format="%Y-%m-%d"),
            alt.Tooltip("btc_close:Q", title="BTC Close", format="$,.2f"),
        ],
    ).transform_calculate(legend="'BTC Price'")

    # 4. Optional reference line for yield curve inversion
    if col == "yield_curve_slope":
        ref_data = pd.DataFrame({"y": [0]})
        ref_line = (
            alt.Chart(ref_data)
            .mark_rule(color="#FF4500", strokeDash=[4, 4], strokeWidth=1.5)
            .encode(y="y:Q")
        )
        combined = alt.layer(macro_line, btc_line, ref_line)
    else:
        combined = alt.layer(macro_line, btc_line)

    # 5. Configuração de Responsividade e Títulos
    chart = (
        combined.resolve_scale(y="independent")
        .properties(
            width="container",  # Permite que o Altair se expanda no container do Streamlit
            height=450,        # Altura ligeiramente reduzida para caber na tela do celular
            title=alt.TitleParams(
                text=f"{meta['legend']} vs BTC", # Título curto
                subtitle=[
                    f"Eixo Esq: {meta['ylabel']}", 
                    "Eixo Dir: BTC (Escala Log)"
                ], # Subtítulo em lista (duas linhas) evita quebra/corte horizontal
                color="white",
                subtitleColor="#aaaaaa",
                fontSize=14,
                subtitleFontSize=11,
                anchor="start",
            ),
            background="#0e1117",
        )
        .configure_view(strokeWidth=0)
    )

    return chart


def create_all_indicator_charts(df, meta = indicator_meta):
    """Returns a dictionary of Plotly figure objects for all indicators in metadata."""
    
    return {
        col: create_indicator_chart(df, col, meta)
        for col, meta in indicator_meta.items()
    }