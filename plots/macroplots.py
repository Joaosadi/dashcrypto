import datetime

import altair as alt
import pandas as pd
import streamlit as st

alt.data_transformers.disable_max_rows()
alt.themes.enable("dark")

FRED_SERIES = {
    "DTWEXBGS": "dxy",
    "DGS10": "us_10y_yield",
    "WALCL": "fed_balance_sheet",
    "T10Y2Y": "yield_curve_slope",
}

INDICATOR_META = {
    "dxy": {
        "title": "US Dollar Index vs Bitcoin",
        "ylabel": "Broad Dollar Index",
        "format": ".1f",
        "zero_line": False,
    },
    "us_10y_yield": {
        "title": "10-Year Treasury Yield vs Bitcoin",
        "ylabel": "10Y Yield (%)",
        "format": ".2f",
        "zero_line": False,
    },
    "fed_balance_sheet": {
        "title": "Fed Total Assets vs Bitcoin",
        "ylabel": "Fed Assets ($T)",
        "format": ".2f",
        "zero_line": False,
    },
    "yield_curve_slope": {
        "title": "10Y–2Y Yield Curve vs Bitcoin",
        "ylabel": "10Y–2Y Slope (pp)",
        "format": ".2f",
        "zero_line": True,
    },
}

LEGEND_RANGE = ["#7FFFD4", "#FF7F50"]


def _axis(**kwargs):
    return alt.Axis(gridColor="#222222", labelColor="#cccccc", titleColor="#cccccc", **kwargs)


def _legend():
    return alt.Legend(
        title="Series",
        orient="top-left",
        fillColor="#0e1117",
        strokeColor="#333333",
        padding=8,
        cornerRadius=5,
        labelColor="#cccccc",
        titleColor="#ffffff",
    )


@st.cache_data(ttl=60 * 60 * 12)
def fetch_fred_macro_data(start_date="2006-01-01", end_date=None):
    """Pull FRED series as CSV (no API key) and align to a daily calendar."""
    if end_date is None:
        end_date = datetime.datetime.now().strftime("%Y-%m-%d")

    frames = []
    for series_id, name in FRED_SERIES.items():
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        raw = pd.read_csv(url, na_values=["."])
        date_col = "observation_date" if "observation_date" in raw.columns else "DATE"
        raw[date_col] = pd.to_datetime(raw[date_col])
        raw = raw.rename(columns={date_col: "date", series_id: name})
        frames.append(raw.set_index("date")[[name]])

    df = pd.concat(frames, axis=1)
    df = df.loc[start_date:end_date]
    full_idx = pd.date_range(start=start_date, end=end_date, freq="D")
    df = df.reindex(full_idx).ffill().bfill()
    df.index.name = "date"
    return df


def merge_macro_btc(macro_df, btc_df):
    """Join FRED daily series to BTC closes on calendar date."""
    macro = macro_df.copy()
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
    merged = macro.join(btc, how="inner").dropna(subset=["btc_close"])
    merged["fed_balance_sheet"] = merged["fed_balance_sheet"] / 1e6
    return merged.reset_index()


def plot_macro_vs_btc(merged, column):
    meta = INDICATOR_META[column]
    data = merged[["date", "btc_close", column]].dropna()
    legend_domain = ["BTC Price", meta["ylabel"]]
    color_scale = alt.Color(
        "legend:N",
        scale=alt.Scale(domain=legend_domain, range=LEGEND_RANGE),
        legend=_legend(),
    )

    btc_line = (
        alt.Chart(data)
        .mark_line(strokeWidth=1.5)
        .encode(
            x=alt.X("date:T", title="Date", axis=_axis()),
            y=alt.Y(
                "btc_close:Q",
                scale=alt.Scale(type="log"),
                title="BTC Price (USD)",
                axis=alt.Axis(
                    gridColor="#222222",
                    labelColor="#cccccc",
                    titleColor="#7FFFD4",
                    format="$,.0f",
                ),
            ),
            color=color_scale,
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("btc_close:Q", format="$,.2f", title="BTC Price"),
            ],
        )
        .transform_calculate(legend="'BTC Price'")
    )

    macro_line = (
        alt.Chart(data)
        .mark_line(strokeWidth=1.5)
        .encode(
            x=alt.X("date:T", title="Date", axis=_axis()),
            y=alt.Y(
                f"{column}:Q",
                title=meta["ylabel"],
                axis=alt.Axis(
                    gridColor="#222222",
                    labelColor="#cccccc",
                    titleColor="#FF7F50",
                    format=meta["format"],
                ),
            ),
            color=color_scale,
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip(f"{column}:Q", format=meta["format"], title=meta["ylabel"]),
            ],
        )
        .transform_calculate(legend=f"'{meta['ylabel']}'")
    )

    layers = [btc_line]
    if meta["zero_line"]:
        zero_rule = (
            alt.Chart(data)
            .mark_rule(color="#FF0000", strokeDash=[4, 4], opacity=0.7)
            .encode(y=alt.datum(0))
        )
        layers.append(alt.layer(macro_line, zero_rule))
    else:
        layers.append(macro_line)

    return (
        alt.layer(*layers)
        .resolve_scale(y="independent")
        .properties(
            height=380,
            title=alt.TitleParams(text=meta["title"], color="white", fontSize=18, anchor="start"),
            background="#0e1117",
        )
        .configure_view(strokeWidth=0)
    )


def plot_all_macro_vs_btc(merged):
    return {col: plot_macro_vs_btc(merged, col) for col in INDICATOR_META}
