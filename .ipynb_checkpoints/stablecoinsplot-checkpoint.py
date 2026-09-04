import requests
import streamlit as st
import pandas as pd
import altair as alt
import time
import numpy as np

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

def get_tether_dominance(df):
    totalcap = df["circulating"].sum()
    thetercap = df[df["symbol"] == "USDT"]["circulating"].values[0]
    return thetercap/totalcap


@st.cache_resource
def plot_stablecoins_market_dominance(df, nstables = 6):
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
        "#AAA0AF",
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
def prepare_top_stablecoin_data(df, nstables = 6):
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
        "USDe": "#E1A0FF",
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


# stable coin histograms

# stablecoin historical prices
@st.cache_data
def get_stablecoin_prices():
    url = "https://stablecoins.llama.fi/stablecoinprices"
    response = requests.get(url)
    data = response.json()
    df_list = []
    for d in data:
        date = d["date"]
        coins = pd.DataFrame(list(d["prices"].items()), columns = ["stablecoin", "price"])
        # print(d["prices"])
        coins["date"] = date
        df_list.append(coins)
    df = pd.concat(df_list)
    df["date"] = pd.to_datetime(df["date"], unit="s")
    df = df[df["date"] != "1970-01-01"]
    return df

@st.cache_resource
def plot_stablecoin_price_histograms(price_df, symbol="usdt"):
    # Case-insensitive filtering
    token_df = price_df[
        price_df["stablecoin"].str.lower() == symbol.lower()
    ].copy()

    if token_df.empty:
        # Fallback if symbol isn't found
        token_df = price_df[
            price_df["stablecoin"].str.contains(symbol, case=False, na=False)
        ].copy()

    # 1. Pre-calculate histogram bins in Pandas to prevent sub-segment stacking
    counts, bin_edges = np.histogram(token_df["price"].dropna(), bins=40)

    binned_df = pd.DataFrame(
        {
            "bin_start": bin_edges[:-1],
            "bin_end": bin_edges[1:],
            "bin_center": (bin_edges[:-1] + bin_edges[1:]) / 2,
            "count": counts,
        }
    )

    color = "#A01236"

    # 2. Plot pre-aggregated bins as clean, single bars
    bars = (
        alt.Chart(binned_df)
        .mark_bar(
            color=color,
            opacity=0.85,
            cornerRadiusTopLeft=3,
            cornerRadiusTopRight=3,
        )
        .encode(
            x=alt.X(
                "bin_center:Q",
                title="Price (USD)",
                axis=alt.Axis(
                    format="$.3f",
                    gridColor="#22272E",
                    domainColor="#444C56",
                    labelColor="#ADB5BD",
                    titleColor="#FFFFFF",
                ),
            ),
            y=alt.Y(
                "count:Q",
                title="Frequency (Days)",
                axis=alt.Axis(
                    gridColor="#22272E",
                    domainColor="#444C56",
                    labelColor="#ADB5BD",
                    titleColor="#FFFFFF",
                ),
            ),
            tooltip=[
                alt.Tooltip("bin_start:Q", title="Bin Start", format="$.4f"),
                alt.Tooltip("bin_end:Q", title="Bin End", format="$.4f"),
                alt.Tooltip("count:Q", title="Days Count"),
            ],
        )
    )

    # $1.00 Peg Baseline Reference Line
    peg_line = (
        alt.Chart(pd.DataFrame([{"peg": 1.00}]))
        .mark_rule(color="#F6465D", strokeDash=[4, 4], strokeWidth=2)
        .encode(x="peg:Q")
    )

    # Combine chart
    chart = (
        (bars + peg_line)
        .properties(
            title=f"{symbol.upper()} Price Distribution",
            width=600,
            height=300,
        )
        .configure_title(
            anchor="middle",
            color="#FFFFFF",
            fontSize=18,
        )
    )

    return chart


# stablecoin per chain and metrics
@st.cache_data
def get_stablecoinchains():

    """ Returns a dataframe with chain, circulating columns"""
    url = "https://stablecoins.llama.fi/stablecoinchains"
    r = requests.get(url).json()
    dictlist = []
    for d in r:
        name = d["name"]
        # print(d["totalCirculatingUSD"])
        try:
            circulating = d["totalCirculatingUSD"]["peggedUSD"]
        except: 
            circulating = 0
        dictlist.append({"chain": name, "circulating": circulating})
    df = pd.DataFrame(dictlist)
    return df

def get_stablecoin_marketcap(df):
    return df["circulating"].sum()


def get_ethereum_stablecoin_dominance(df):
    return df[df["chain"] == "Ethereum"]["circulating"].values[0]/get_stablecoin_marketcap(df)


@st.cache_resource
def plot_chain_stablecoin_dominance(df):
    # 1. Sort and group chains outside top 4 into 'Others'
    top_n = 5
    df_sorted = df.sort_values(by="circulating", ascending=False).reset_index(
        drop=True
    )
    
    top_chains = df_sorted.iloc[:top_n].copy()
    others_value = df_sorted.iloc[top_n:]["circulating"].sum()
    
    if others_value > 0:
        others_df = pd.DataFrame(
            [{"chain": "Others", "circulating": others_value}]
        )
        df_grouped = pd.concat([top_chains, others_df], ignore_index=True)
    else:
        df_grouped = top_chains
    
    # 2. Calculate percentage share
    total_circulating = df_grouped["circulating"].sum()
    df_grouped["pct"] = df_grouped["circulating"] / total_circulating
    
    # 3. Define custom color mappings (including a specific color for 'Others')
    domain = list(df_grouped["chain"])
    color_palette = {
        "Ethereum": "#627EEA",
        "Tron": "#FF0013",
        "Solana": "#14F195",
        "BSC": "#F3BA2F",
        "Hyperliquid L1": "#00AEE9",
        "Others": "#6E7681",  # Neutral dark gray for 'Others'
    }
    
    range_colors = [color_palette.get(chain, "#9E9E9E") for chain in domain]
    
    # 4. Plot pie/donut chart
    # 2. Base encoding for both pie arc and text marks
    base = alt.Chart(df_grouped).encode(
        theta=alt.Theta("pct:Q", stack=True),
        color=alt.Color(
            "chain:N",
            title="Blockchain",
            scale=alt.Scale(domain=domain, range=range_colors),
            legend=alt.Legend(
                labelColor="#FFFFFF", titleColor="#FFFFFF", orient="right"
            ),
            sort=domain,
        ),
    )
    
    # 3. Donut Arc Layer
    arcs = base.mark_arc(innerRadius=0, outerRadius=150).encode(
        tooltip=[
            alt.Tooltip("chain:N", title="Chain"),
            alt.Tooltip("pct:Q", title="Share", format=".1%"),
            alt.Tooltip(
                "circulating:Q", title="Circulating Supply", format="$,.0f"
            ),
        ]
    )
    
    # 4. Text Label Layer inside slices
    labels = base.mark_text(
        radius=180,  # Position labels between innerRadius (80) and outerRadius (150)
        color="white",
        fontSize=12,
        fontWeight="bold",
    ).encode(
        text=alt.Text("pct:Q", format=".1%")  # Displays formatted percentage (e.g. 58.2%)
    )
    
    # 5. Combine layers
    chart = (
        (arcs + labels)
        .properties(
            title="Stablecoin Market Share by Chain (%)",
            width=400,
            height=500,
            background="#0E1117",
        )
        .configure_title(anchor="middle", color="#FFFFFF", fontSize=16)
        .configure_view(strokeWidth=0)
    )
    return chart