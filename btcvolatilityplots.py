import pandas as pd
import streamlit as st
import scipy
import numpy as np
import altair as alt

@st.cache_resource
def plot_btc_volatility(df_raw, period = 30):
    data = df_raw.copy()

    # 1. Clean price data and sort
    data["time_close"] = pd.to_datetime(data["time_close"])
    data["close"] = pd.to_numeric(
        data["close"].astype(str).str.replace("$", "").str.replace(",", ""),
        errors="coerce",
    )
    data = (
        data.dropna(subset=["close"])
        .sort_values("time_close")
        .reset_index(drop=True)
    )

    # 2. Calculate 30-Day Annualized Volatility
    data["daily_return"] = data["close"].pct_change(1)
    # 30-day rolling std dev scaled to 365 trading days
    data["volatility_30d"] = (
        data["daily_return"].rolling(window=period).std() * np.sqrt(365) * 100
    )

    # 3. Master Legend Scale
    legend_domain = ["BTC Price", f"{period}D Volatility (Annualized)"]
    legend_range = ["#7FFFD4", "#FF7F50"]  # Aquamarine & Coral/Orange

    color_scale = alt.Color(
        "legend:N",
        scale=alt.Scale(domain=legend_domain, range=legend_range),
        legend=alt.Legend(
            title="Model Traces",
            orient="top-left",
            fillColor="#0e1117",
            strokeColor="#333333",
            padding=8,
            cornerRadius=5,
            labelColor="#cccccc",
            titleColor="#ffffff",
        ),
    )

    # 4. Top Chart - BTC Price (Log Scale)
    top_chart = (
        alt.Chart(data[["time_close", "close"]])
        .mark_line(strokeWidth=1.5)
        .encode(
            x=alt.X(
                "time_close:T",
                title=None,
                axis=alt.Axis(
                    gridColor="#222222", labelColor="#cccccc", labels=False
                ),
            ),
            y=alt.Y(
                "close:Q",
                scale=alt.Scale(type="log"),
                title="Price (USD)",
                axis=alt.Axis(gridColor="#222222", labelColor="#cccccc"),
            ),
            color=color_scale,
            tooltip=[
                alt.Tooltip("time_close:T", title="Date"),
                alt.Tooltip("close:Q", format="$,.2f", title="Price"),
            ],
        )
        .transform_calculate(legend="'BTC Price'")
        .properties(width=900, height=380)
    )

    # 5. Bottom Chart - 30-Day Rolling Volatility
    bottom_chart = (
        alt.Chart(
            data.dropna(subset=["volatility_30d"])[
                ["time_close", "volatility_30d"]
            ]
        )
        .mark_line(strokeWidth=1.5)
        .encode(
            x=alt.X(
                "time_close:T",
                title="Date",
                axis=alt.Axis(gridColor="#222222", labelColor="#cccccc"),
            ),
            y=alt.Y(
                "volatility_30d:Q",
                title="30D Volatility (%)",
                axis=alt.Axis(
                    gridColor="#222222", labelColor="#cccccc", format=".0f"
                ),
            ),
            color=color_scale,
            tooltip=[
                alt.Tooltip("time_close:T", title="Date"),
                alt.Tooltip(
                    "volatility_30d:Q", format=".2f", title="30D Volatility (%)"
                ),
            ],
        )
        .transform_calculate(legend="'30D Volatility (Annualized)'")
        .properties(width=900, height=180)
    )

    # 6. Stack vertically
    combined_chart = (
        alt.vconcat(top_chart, bottom_chart)
        .resolve_scale(x="shared")
        .properties(
            title=alt.TitleParams(
                text="Bitcoin Price & 30-Day Annualized Volatility",
                color="white",
                fontSize=18,
                anchor="start",
            ),
            background="#0e1117",
            bounds="full",
        )
        .configure_view(strokeWidth=0)
    )

    return combined_chart



# volatility bands
@st.cache_resource
def plot_btc_volatility_bands(
    df_raw, vol_window=30, sma_window=20, num_std=3
):
    data = df_raw.copy().reset_index()

    # 1. Flexible date column detection and parsing
    date_col = next(
        (
            col
            for col in ["time_close", "Date", "date", "timestamp", "index"]
            if col in data.columns
        ),
        data.columns[0],
    )
    data["clean_date"] = pd.to_datetime(data[date_col])

    # 2. Flexible price column detection and cleaning
    price_col = next(
        (
            col
            for col in ["close", "Close", "price", "Price"]
            if col in data.columns
        ),
        None,
    )
    if not price_col:
        raise ValueError("No price/close column found in dataframe.")

    data["clean_price"] = pd.to_numeric(
        data[price_col].astype(str).str.replace("$", "").str.replace(",", ""),
        errors="coerce",
    )

    # Clean & Sort
    clean_df = (
        data.dropna(subset=["clean_date", "clean_price"])
        .sort_values("clean_date")
        .reset_index(drop=True)
    )

    # 3. Indicator Calculations
    clean_df["daily_return"] = clean_df["clean_price"].pct_change(1)
    clean_df["daily_std_30d"] = (
        clean_df["daily_return"].rolling(window=vol_window).std()
    )

    clean_df["price_sma"] = (
        clean_df["clean_price"].rolling(window=sma_window).mean()
    )
    clean_df["upper_band"] = clean_df["price_sma"] * (
        1 + (num_std * clean_df["daily_std_30d"])
    )
    clean_df["lower_band"] = clean_df["price_sma"] * (
        1 - (num_std * clean_df["daily_std_30d"])
    )

    plot_data = clean_df.dropna(subset=["upper_band"]).copy()

    # 4. Color Scale Legend Definition
    legend_domain = [
        "BTC Price",
        f"{sma_window}D Price SMA",
        f"±{num_std} Std Dev Bands",
    ]
    legend_range = ["#7FFFD4", "#1E90FF", "#888888"]

    color_scale = alt.Color(
        "legend:N",
        scale=alt.Scale(domain=legend_domain, range=legend_range),
        legend=alt.Legend(
            title="Model Traces",
            orient="top-left",
            fillColor="#0e1117",
            strokeColor="#333333",
            padding=8,
            cornerRadius=5,
            labelColor="#cccccc",
            titleColor="#ffffff",
        ),
    )

    # --- PRICE & BANDS LAYERS ---
    # Shaded Band Area
    band_area = (
        alt.Chart(plot_data)
        .mark_area(opacity=0.15, color="#888888")
        .encode(
            x="clean_date:T",
            y="lower_band:Q",
            y2="upper_band:Q",
        )
    )

    # Band Boundary Lines
    band_lines = (
        alt.Chart(
            plot_data.melt(
                id_vars=["clean_date"],
                value_vars=["upper_band", "lower_band"],
                var_name="band_type",
                value_name="band_val",
            )
        )
        .mark_line(strokeDash=[4, 4], strokeWidth=1)
        .encode(
            x="clean_date:T",
            y=alt.Y("band_val:Q", scale=alt.Scale(type="log")),
            color=color_scale,
            tooltip=[
                alt.Tooltip("clean_date:T", title="Date"),
                alt.Tooltip(
                    "band_val:Q", format="$,.2f", title="Band Value"
                ),
            ],
        )
        .transform_calculate(legend=f"'±{num_std} Std Dev Bands'")
    )

    # Price SMA
    sma_line = (
        alt.Chart(plot_data)
        .mark_line(strokeWidth=1.5)
        .encode(
            x="clean_date:T",
            y="price_sma:Q",
            color=color_scale,
            tooltip=[
                alt.Tooltip("clean_date:T", title="Date"),
                alt.Tooltip("price_sma:Q", format="$,.2f", title="SMA"),
            ],
        )
        .transform_calculate(legend=f"'{sma_window}D Price SMA'")
    )

    # BTC Price Line
    price_line = (
        alt.Chart(plot_data)
        .mark_line(strokeWidth=1.5)
        .encode(
            x=alt.X(
                "clean_date:T",
                title="Date",
                axis=alt.Axis(gridColor="#222222", labelColor="#cccccc"),
            ),
            y=alt.Y(
                "clean_price:Q",
                scale=alt.Scale(type="log"),
                title="Price (USD)",
                axis=alt.Axis(gridColor="#222222", labelColor="#cccccc"),
            ),
            color=color_scale,
            tooltip=[
                alt.Tooltip("clean_date:T", title="Date"),
                alt.Tooltip("clean_price:Q", format="$,.2f", title="Price"),
            ],
        )
        .transform_calculate(legend="'BTC Price'")
    )

    # Combine into a single interactive chart
    chart = (
        alt.layer(band_area, band_lines, sma_line, price_line)
        .properties(
            width=900,
            height=500,
            title=alt.TitleParams(
                text="Bitcoin Price with 30-Day Volatility Bands Indicator",
                subtitle=f"Bands: {sma_window}-Day SMA ± {num_std} Standard Deviations of Volatility",
                color="white",
                subtitleColor="#aaaaaa",
                fontSize=18,
                anchor="start",
            ),
            background="#0e1117",
        )
        .configure_view(strokeWidth=0)
        .interactive()
    )

    return chart


# rvi

def calculate_rvi(df: pd.DataFrame, std_period: int = 10, smooth_period: int = 14) -> pd.Series:
    """
    Calculates Donald Dorsey's Relative Volatility Index (RVI).
    
    Parameters:
    - df: DataFrame with 'close', 'high', and 'low' columns.
    - std_period: Rolling window for standard deviation (default: 10).
    - smooth_period: Exponential smoothing window (Wilder's RSI-style, default: 14).
    """
    # 1. Calculate standard deviation of Highs and Lows over std_period
    std_high = df['high'].rolling(window=std_period).std(ddof=0)
    std_low = df['low'].rolling(window=std_period).std(ddof=0)
    
    # Average the standard deviation of high and low
    std_avg = (std_high + std_low) / 2.0
    
    # 2. Determine price direction relative to previous close
    change = df['close'].diff()
    
    # Separate directional volatility
    u_vol = np.where(change > 0, std_avg, 0.0)
    d_vol = np.where(change < 0, std_avg, 0.0)
    
    # 3. Apply Exponential Moving Average (Wilder's Smoothing)
    # alpha = 1 / smooth_period matches Wilder's EMA standard for RSI/RVI
    u_ema = pd.Series(u_vol, index=df.index).ewm(alpha=1/smooth_period, adjust=False).mean()
    d_ema = pd.Series(d_vol, index=df.index).ewm(alpha=1/smooth_period, adjust=False).mean()
    
    # 4. Calculate RVI bounded between 0 and 100
    rvi = 100 * (u_ema / (u_ema + d_ema))
    
    return rvi


@st.cache_resource
def plot_rvi(df_raw, std_period=10, smooth_period=14):
    data = df_raw.copy().reset_index()
    data["rvi"] = calculate_rvi(data)
    
    # Detect Date Column
    date_col = next(
        (
            col
            for col in ["time_close", "Date", "date", "timestamp", "index"]
            if col in data.columns
        ),
        data.columns[0],
    )
    data["clean_date"] = pd.to_datetime(data[date_col])

    # Calculate RVI
    data["rvi"] = calculate_rvi(
        data, std_period=std_period, smooth_period=smooth_period
    )
    plot_data = data.dropna(subset=["clean_date", "rvi"]).copy()

    # Reference Threshold DataFrames
    rect_data = pd.DataFrame(
        [
            {"y1": 80, "y2": 100, "zone": "Overbought / Bullish Volatility"},
            {"y1": 0, "y2": 20, "zone": "Oversold / Bearish Volatility"},
        ]
    )

    lines_data = pd.DataFrame(
        [
            {"val": 50, "type": "Neutral (50)"},
            {"val": 80, "type": "Upper Band (80)"},
            {"val": 20, "type": "Lower Band (20)"},
        ]
    )

    # --- ALTAIR LAYERS ---
    # Shaded Extremes (0-20 and 80-100)
    shading = (
        alt.Chart(rect_data)
        .mark_rect(opacity=0.08)
        .encode(
            y="y1:Q",
            y2="y2:Q",
            color=alt.Color(
                "zone:N",
                scale=alt.Scale(
                    domain=[
                        "Overbought / Bullish Volatility",
                        "Oversold / Bearish Volatility",
                    ],
                    range=["#FF4500", "#00FF7F"],
                ),
                legend=None,
            ),
        )
    )

    # Horizontal Lines at 20, 50, 80
    reference_lines = (
        alt.Chart(lines_data)
        .mark_rule(strokeDash=[4, 4], strokeWidth=1, color="#666666")
        .encode(y="val:Q")
    )

    # Main RVI Line
    rvi_line = (
        alt.Chart(plot_data)
        .mark_line(strokeWidth=1.8, color="#8B5CF6")
        .encode(
            x=alt.X(
                "clean_date:T",
                title="Date",
                axis=alt.Axis(gridColor="#222222", labelColor="#cccccc"),
            ),
            y=alt.Y(
                "rvi:Q",
                title="RVI (0-100)",
                scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(gridColor="#222222", labelColor="#cccccc"),
            ),
            tooltip=[
                alt.Tooltip("clean_date:T", title="Date"),
                alt.Tooltip("rvi:Q", format=".2f", title="RVI"),
            ],
        )
    )

    # Combined Chart
    chart = (
        alt.layer(shading, reference_lines, rvi_line)
        .properties(
            width=900,
            height=600,
            title=alt.TitleParams(
                text="Relative Volatility Index (RVI)",
                subtitle=f"Donald Dorsey RVI ({std_period}-Period StdDev, {smooth_period}-Period Wilder Smoothing)",
                color="white",
                subtitleColor="#aaaaaa",
                fontSize=16,
                anchor="start",
            ),
            background="#0e1117",
        )
        .configure_view(strokeWidth=0)
    )

    return chart

