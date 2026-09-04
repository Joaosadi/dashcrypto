import requests
import streamlit as st
import pandas as pd
import altair as alt
import time

@st.cache_data
def get_stablecoin_circulating_data():
    url = "https://stablecoins.llama.fi/stablecoins"
    response = requests.get(url)
    data = response.json()["peggedAssets"]
    dict_list = []
    for coin in data:
        # for some reason this is very confusing to work
        circ = list(coin["circulating"].values())[0]
        d = {"id": coin["id"], "name": coin["name"], "symbol": coin["symbol"], "circulating": circ}
        dict_list.append(d)
    df = pd.DataFrame(dict_list)
    return df


@st.cache_resource
def plot_stablecoins_market_dominance(df, nstables = 5):
    # 1. Sort dataframe by circulating supply descending
    df_sorted = df.sort_values("circulating", ascending=False)
    
    # 2. Extract top 5 and group the rest into "Others"
    top_5 = df_sorted.head(nstables).copy()
    others_sum = df_sorted.iloc[nstables:]["circulating"].sum()
    
    # Create a combined dataframe for plotting
    others_df = pd.DataFrame([{"symbol": "Others", "circulating": others_sum}])
    plot_df = pd.concat([top_5[["symbol", "circulating"]], others_df], ignore_index=True)

    # Calculate percentage column
    total_circulating = plot_df["circulating"].sum()
    plot_df["percentage"] = (plot_df["circulating"] / total_circulating) * 100
    plot_df["percent_label"] = plot_df["percentage"].map("{:.1f}%".format)
    
    # 2. Define your Streamlit app colors (replace these hex codes with your actual app colors)
    my_custom_colors = [
        "#00FFAA", # Color 1 (e.g., Tether)
        "#00AAFF", # Color 2 (e.g., USD Coin)
        "#FF00AA", # Color 3
        "#FFAA00", # Color 4
        "#AA00FF", # Color 5
        "#555555"  # Others (usually greyed out in dark themes)
    ]

    
    # 3. Base Chart Encoding
    base = alt.Chart(plot_df).encode(
        theta=alt.Theta(field="circulating", type="quantitative", stack=True),
        color=alt.Color(
            field="symbol",
            type="nominal",
            sort=None,
            scale=alt.Scale(range=my_custom_colors),
            title="Stablecoin",
        ),
        order=alt.Order(field="circulating", type="quantitative", sort="ascending"),
    )
    
    # 4. Slices (Pie Layer)
    pie = base.mark_arc(outerRadius=200, stroke="#0E1117", strokeWidth=2)
    
    # 5. Percentage Labels Layer
    text = base.mark_text(
        radius=250,  # Controls label distance from center (inside the slice)
        fill="white",  # Text color
        fontWeight="bold",
        fontSize=16,
    ).encode(
        text=alt.Text("percent_label:N"),
        tooltip=[
            "symbol",
            alt.Tooltip("circulating:Q", format=",.0f"),
            alt.Tooltip("percent_label:N", title="Percentage"),
        ],
    )
    
    # 6. Combine layers
    chart = (
        (pie + text)
        .properties(
            title=f"Top {nstables} Stablecoins by Circulating Supply",
            width=600,
            height=600,
            background="#0e1117",
        )
        .configure_title(color="white")
        .configure_legend(labelColor="white", titleColor="white")
    )

    return chart

# historical data

@st.cache_data
def get_stablecoin_historical_data(id="1"):
    
    url = f"https://stablecoins.llama.fi/stablecoin/{id}"
    r = requests.get(url).json()
    
    dictlist = []
    for chain, data in r["chainBalances"].items():
        datalist = data["tokens"]
        for d in datalist:
            try:
                date = pd.to_datetime(d["date"], unit="s")
                circulating = d["circulating"]["peggedUSD"]
                dictlist.append({"date": date, "circulating": circulating, "symbol": r["symbol"], "chain": chain})
            except:
                # print("This went wrong:", d)
                continue
    df = pd.DataFrame(dictlist)
    return df

@st.cache_data
def prepare_top_stablecoin_data(df, nstables = 5):
    df_sorted = df.sort_values("circulating", ascending = False)
    ids = df_sorted["id"].head(nstables)
    series_dict = dict()
    for id in ids:
        # print(f"Downloading data for id {id}.")
        time.sleep(1)
        coindata = get_stablecoin_historical_data(id=id)
        symbol = coindata["symbol"].values[0]
        coindata = coindata.groupby("date")["circulating"].sum()
        series_dict[symbol] = coindata
        # print(f"Finished data for id {id}.")

    result = pd.concat(series_dict, axis = 1).fillna(0)
    result = result.sort_index().reset_index()
    df_long = result.melt(id_vars=["date"], var_name="symbol", value_name="circulating")
    df_long["circulating_b"] = df_long["circulating"].astype(float) / 1e9
    return df_long


@st.cache_resource
def plot_stablecoin_historical_circulating(prepared_data, normalize=False):
    # 1. Fill missing data & resample weekly
    prepared_data = prepared_data.copy()
    prepared_data["circulating_b"] = prepared_data["circulating_b"].fillna(0.0)

    df_weekly = (
        prepared_data.set_index("date")
        .groupby("symbol")
        .resample("W")["circulating_b"]
        .mean()
        .reset_index()
    )

    # 2. Build complete date/symbol grid to prevent stack breaks
    all_dates = df_weekly["date"].unique()
    all_symbols = df_weekly["symbol"].unique()

    full_grid = pd.MultiIndex.from_product(
        [all_dates, all_symbols], names=["date", "symbol"]
    ).to_frame().reset_index(drop=True)

    df_weekly = pd.merge(
        full_grid, df_weekly, on=["date", "symbol"], how="left"
    )
    df_weekly["circulating_b"] = df_weekly["circulating_b"].fillna(0.0)

    # 3. Order symbols by latest total circulating supply
    latest_date = df_weekly["date"].max()
    latest_values = df_weekly[df_weekly["date"] == latest_date].sort_values(
        by="circulating_b", ascending=False
    )

    sorted_symbols = latest_values["symbol"].tolist()

    if "Others" in sorted_symbols:
        sorted_symbols.remove("Others")
        sorted_symbols.append("Others")

    df_weekly["symbol_order"] = pd.Categorical(
        df_weekly["symbol"], categories=sorted_symbols, ordered=True
    )

    # 4. Color Mapping with Dynamic Fallbacks (Fixes Omitted Symbols)
    base_color_map = {
        "USDT": "#00FFAA",
        "USDC": "#00AAFF",
        "DAI": "#FF00AA",
        "USDS": "#FFAA00",
        "USD1": "#AA00FF",
        "USDe": "#E100FF",
        "PYUSD": "#00E5FF",
        "Others": "#6E7681",
    }

    fallback_palette = [
        "#FF5722",
        "#E91E63",
        "#9C27B0",
        "#3F51B5",
        "#00BCD4",
        "#8BC34A",
    ]

    domain = sorted_symbols
    range_colors = []

    fallback_idx = 0
    for sym in domain:
        if sym in base_color_map:
            range_colors.append(base_color_map[sym])
        else:
            # Assign a fallback color if symbol isn't hardcoded
            range_colors.append(
                fallback_palette[fallback_idx % len(fallback_palette)]
            )
            fallback_idx += 1

    # Chart Configuration
    stack_mode = "normalize" if normalize else "zero"
    y_title = (
        "Market Share Percentage"
        if normalize
        else "Total Circulating Supply ($ Billions)"
    )
    y_format = ".0%" if normalize else "$~s"
    chart_title = (
        "Stablecoin Market Share Over Time (%)"
        if normalize
        else "Stablecoin Circulating Supply Over Time"
    )

    # 5. Render Altair Chart
    chart = (
        alt.Chart(df_weekly)
        .mark_area(opacity=0.85, stroke="rgba(255,255,255,0.1)", strokeWidth=0.5)
        .encode(
            x=alt.X(
                "date:T",
                title="Date",
                axis=alt.Axis(
                    format="%b %Y",
                    gridColor="#22272E",
                    domainColor="#444C56",
                    labelColor="#ADB5BD",
                    titleColor="#FFFFFF",
                ),
            ),
            y=alt.Y(
                "circulating_b:Q",
                title=y_title,
                stack=stack_mode,
                axis=alt.Axis(
                    format=y_format,
                    gridColor="#22272E",
                    domainColor="#444C56",
                    labelColor="#ADB5BD",
                    titleColor="#FFFFFF",
                ),
            ),
            color=alt.Color(
                "symbol:N",
                title="Stablecoin",
                scale=alt.Scale(domain=domain, range=range_colors),
                legend=alt.Legend(
                    labelColor="#FFFFFF",
                    titleColor="#FFFFFF",
                    orient="right",
                ),
                sort=sorted_symbols,
            ),
            order=alt.Order("symbol_order:N", sort="descending"),
            tooltip=[
                alt.Tooltip("date:T", title="Date", format="%b %d, %Y"),
                alt.Tooltip("symbol:N", title="Token"),
                alt.Tooltip(
                    "circulating_b:Q", title="Circulating ($B)", format="$.2f"
                ),
            ],
        )
        .properties(
            title=chart_title,
            width="container",
            height=600,
            background="#0e1117",
        )
        .configure_title(color="#FFFFFF", fontSize=18)
        .configure_view(strokeWidth=0)
    )

    return chart

@st.cache_resource
def plot_stablecoin_price_histograms(price_df, symbol = "USDT"):
    """Generates price distribution histograms for individual stablecoins.

    Expects `price_df` with columns: ['date', 'symbol', 'price']
    """
    color_map = {
        "USDT": "#00FFAA",
        "USDC": "#00AAFF",
        "DAI": "#FF00AA",
        "USDS": "#FFAA00",
        "USD1": "#AA00FF",
        "USDE": "#E100FF",
        "PYUSD": "#00E5FF",
        "Others": "#6E7681",
    }

    token_df = price_df[price_df["symbol"] == symbol].copy()
    color = color_map.get(symbol, "#00AAFF")

    # Histogram Bars
    bars = (
        alt.Chart(token_df)
        .mark_bar(
            opacity=0.75,
            color=color,
            cornerRadiusTopLeft=2,
            cornerRadiusTopRight=2,
        )
        .encode(
            x=alt.X(
                "price:Q",
                title="Price (USD)",
                bin=alt.BinParams(maxbins=40),
                axis=alt.Axis(
                    format="$.3f",
                    gridColor="#22272E",
                    domainColor="#444C56",
                    labelColor="#ADB5BD",
                    titleColor="#FFFFFF",
                ),
            ),
            y=alt.Y(
                "count():Q",
                title="Frequency (Days)",
                axis=alt.Axis(
                    gridColor="#22272E",
                    domainColor="#444C56",
                    labelColor="#ADB5BD",
                    titleColor="#FFFFFF",
                ),
            ),
            tooltip=[
                alt.Tooltip("price:Q", title="Price Bin", format="$.4f"),
                alt.Tooltip("count():Q", title="Days Count"),
            ],
        )
    )

    # # $1.00 Peg Baseline Reference Line
    # peg_line = (
    #     alt.Chart(pd.DataFrame([{"peg": 1.00}]))
    #     .mark_rule(color="#F6465D", strokeDash=[4, 4], strokeWidth=1.5)
    #     .encode(x="peg:Q")
    # )

    # # Combine sub-chart (NO .configure_* calls here!)
    # sub_chart = (bars + peg_line).properties(
    #     title=f"{symbol} Price Distribution",
    #     width=600,
    #     height=300,
    # )

    # charts.append(sub_chart)

    # # Apply global styling once on the top-level concatenated chart
    # final_grid = (
    #     alt.vconcat(*rows)
    #     .properties(background="#0E1117")
    #     .configure_title(color="#FFFFFF", fontSize=14, anchor="start")
    #     .configure_view(strokeWidth=0)
    #     .configure_legend(labelColor="#FFFFFF", titleColor="#FFFFFF")
    # )

    return bars