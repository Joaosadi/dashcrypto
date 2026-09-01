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
            background="transparent",
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

def plot_stablecoin_historical_circulating(prepared_data, normalize=False):

    # Resample to weekly frequency
    df_weekly = (
        prepared_data.set_index("date")
        .groupby("symbol")
        .resample("W")["circulating_b"]
        .mean()
        .reset_index()
    )
    # Find the latest date in your dataset
    latest_date = df_weekly["date"].max()
    
    # Get the circulating supply at the latest date and sort descending
    latest_values = (
        df_weekly[df_weekly["date"] == latest_date]
        .sort_values(by="circulating_b", ascending=False)
    )
    
    # Extract sorted list of symbols based on their final values
    sorted_symbols = latest_values["symbol"].tolist()
    
    # Ensure "Others" is moved to the end if present
    if "Others" in sorted_symbols:
        sorted_symbols.remove("Others")
        sorted_symbols.append("Others")

    df_weekly["symbol_order"] = pd.Categorical(df_weekly["symbol"], categories=sorted_symbols, ordered=True)

    # define chart things dinamically
    stack_mode = "normalize" if normalize else "zero"
    y_title = "Market Share Percentage" if normalize else "Total Circulating Supply ($ Billions)"
    y_format = ".0%" if normalize else "$~s"
    chart_title = "Stablecoin Market Share Over Time (%)" if normalize else "Stablecoin Circulating Supply Over Time"
    
    # Define explicit symbol-to-color mapping
    color_map = {
        "USDT": "#00FFAA",  # Mint Green
        "USDC": "#00AAFF",  # Electric Blue
        "DAI": "#FF00AA",   # Neon Pink
        "USDS": "#FFAA00",  # Vivid Amber
        "USD1": "#AA00FF",  # Vibrant Purple
        "Others": "#6E7681",# Muted Slate Gray
    }
    
    # Match colors directly to the sorted symbol order
    domain = [s for s in sorted_symbols if s in color_map]
    range_colors = [color_map[s] for s in domain]
    
    # Build the chart
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
                sort=sorted_symbols,  # Legend sorted by last value
            ),
            # Order layers by the sorted order array
            order=alt.Order("symbol_order:O", sort="descending"),
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
            background="transparent",
        )
        .configure_title(color="#FFFFFF", fontSize=18)
        .configure_view(strokeWidth=0)
    )
    return chart