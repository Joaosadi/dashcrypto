import requests
import streamlit as st
import pandas as pd
import altair as alt
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
def plot_stablecoins_market_dominance(df, nstables=6):
    df_sorted = df.sort_values(by="circulating", ascending=False).reset_index(
        drop=True
    )

    top_coins = df_sorted.iloc[:nstables].copy()
    others_value = df_sorted.iloc[nstables:]["circulating"].sum()

    if others_value > 0:
        others_df = pd.DataFrame(
            [{"symbol": "Others", "circulating": others_value}]
        )
        df_grouped = pd.concat([top_coins, others_df], ignore_index=True)
    else:
        df_grouped = top_coins

    total_circulating = df_grouped["circulating"].sum()
    df_grouped["pct"] = df_grouped["circulating"] / total_circulating

    domain = list(df_grouped["symbol"])
    color_palette = {
        "USDT": "#00FFAA",
        "USDC": "#00AAFF",
        "DAI": "#FF00AA",
        "USDS": "#FFAA00",
        "USD1": "#AA00FF",
        "USDe": "#E1A0FF",
        "PYUSD": "#00E5FF",
        "Others": "#6E7681",
    }
    range_colors = [color_palette.get(sym, "#9E9E9E") for sym in domain]

    base = alt.Chart(df_grouped).encode(
        theta=alt.Theta("pct:Q", stack=True),
        color=alt.Color(
            "symbol:N",
            title=None,
            scale=alt.Scale(domain=domain, range=range_colors),
            legend=alt.Legend(
                    orient="bottom",
                    direction="horizontal",
                    columns=4,           # Quebra os itens em no máximo 4 colunas por linha
                    symbolLimit=10,      # Garante a exibição de todos os itens
                    labelColor="#FFFFFF",
                    labelFontSize=10,
                    padding=10           # Garante respiro entre o gráfico e a legenda
                ),
            sort=domain,
        ),
    )

    # Reduzido o raio externo para evitar transbordo em telas pequenas
    arcs = base.mark_arc(innerRadius=40, outerRadius=110).encode(
        tooltip=[
            alt.Tooltip("symbol:N", title="Stablecoin"),
            alt.Tooltip("pct:Q", title="Share", format=".1%"),
            alt.Tooltip(
                "circulating:Q", title="Circulating Supply", format="$,.0f"
            ),
        ]
    )

    # Posicionado a label de porcentagem dentro/borda da fatia (radius=130 em vez de 180)
    labels = base.mark_text(
        radius=130, color="white", fontSize=11, fontWeight="bold"
    ).encode(text=alt.Text("pct:Q", format=".1%"))

    chart = (
        (arcs + labels)
        .properties(
            title="Top Stablecoins Market Share",
            width="container",
            height=360,  # Ligeiro aumento para dar respiro
            padding={"top": 30, "bottom": 10, "left": 10, "right": 10}, # Garante espaço em volta
            background="#0E1117",
        )
        .configure_title(
            anchor="middle",
            color="#FFFFFF",
            fontSize=15,
            dy=10  # Empurra o título levemente para DENTRO da área visível (evita o corte no topo)
        )
        .configure_view(strokeWidth=0)
    )
    return chart

# historical data

@st.cache_data
def get_stablecoin_historical_data(id="1"):
    # Lightweight per-day total across all chains (~0.5 MB) instead of the
    # ~20 MB chainBalances payload from /stablecoin/{id}.
    url = f"https://stablecoins.llama.fi/stablecoincharts/all?stablecoin={id}"
    r = requests.get(url, timeout=60).json()

    dictlist = []
    for d in r:
        circ = d["totalCirculating"].get("peggedUSD")
        if circ is None:
            continue
        dictlist.append({"date": pd.to_datetime(int(d["date"]), unit="s"), "circulating": circ})
    return pd.DataFrame(dictlist)

@st.cache_data
def prepare_top_stablecoin_data(df, nstables = 6):
    df_sorted = df.sort_values("circulating", ascending = False).head(nstables)
    series_dict = dict()
    for id, symbol in zip(df_sorted["id"], df_sorted["symbol"]):
        coindata = get_stablecoin_historical_data(id=id)
        coindata = coindata.groupby("date")["circulating"].sum()
        series_dict[symbol] = coindata

    result = pd.concat(series_dict, axis = 1).fillna(0)
    result = result.sort_index().reset_index()
    df_long = result.melt(id_vars=["date"], var_name="symbol", value_name="circulating")
    df_long["circulating_b"] = df_long["circulating"].astype(float) / 1e9
    return df_long


@st.cache_resource
def plot_stablecoin_historical_circulating(prepared_data, normalize=False):
    prepared_data = prepared_data.copy()
    prepared_data["circulating_b"] = prepared_data["circulating_b"].fillna(0.0)

    df_weekly = (
        prepared_data.set_index("date")
        .groupby("symbol")
        .resample("W")["circulating_b"]
        .mean()
        .reset_index()
    )

    all_dates = df_weekly["date"].unique()
    all_symbols = df_weekly["symbol"].unique()

    full_grid = (
        pd.MultiIndex.from_product(
            [all_dates, all_symbols], names=["date", "symbol"]
        )
        .to_frame()
        .reset_index(drop=True)
    )

    df_weekly = pd.merge(
        full_grid, df_weekly, on=["date", "symbol"], how="left"
    )
    df_weekly["circulating_b"] = df_weekly["circulating_b"].fillna(0.0)

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
            range_colors.append(
                fallback_palette[fallback_idx % len(fallback_palette)]
            )
            fallback_idx += 1

    stack_mode = "normalize" if normalize else "zero"
    y_title = "Share (%)" if normalize else "Supply ($B)"
    y_format = ".0%" if normalize else "$~s"
    chart_title = (
        "Market Share Over Time (%)"
        if normalize
        else "Circulating Supply Over Time"
    )

    chart = (
        alt.Chart(df_weekly)
        .mark_area(opacity=0.85, stroke="rgba(255,255,255,0.1)", strokeWidth=0.5)
        .encode(
            x=alt.X(
                "date:T",
                title=None,
                axis=alt.Axis(
                    format="%b %Y",
                    gridColor="#22272E",
                    domainColor="#444C56",
                    labelColor="#ADB5BD",
                    labelAngle=-45,  # Inclinação previne sobreposição de datas no mobile
                    labelFontSize=10,
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
                    labelFontSize=10,
                    titleFontSize=11,
                ),
            ),
            color=alt.Color(
                "symbol:N",
                title=None,
                scale=alt.Scale(domain=domain, range=range_colors),
                legend=alt.Legend(
                    orient="bottom",  # Move legenda para baixo
                    direction="horizontal",
                    labelColor="#FFFFFF",
                    labelFontSize=11,
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
            height=350,  # Reduzido de 600 para 350px para caber na tela do celular
            background="#0e1117",
        )
        .configure_title(color="#FFFFFF", fontSize=15, anchor="start")
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
    token_df = price_df[
        price_df["stablecoin"].str.lower() == symbol.lower()
    ].copy()

    if token_df.empty:
        token_df = price_df[
            price_df["stablecoin"].str.contains(symbol, case=False, na=False)
        ].copy()

    counts, bin_edges = np.histogram(token_df["price"].dropna(), bins=30)

    binned_df = pd.DataFrame(
        {
            "bin_start": bin_edges[:-1],
            "bin_end": bin_edges[1:],
            "bin_center": (bin_edges[:-1] + bin_edges[1:]) / 2,
            "count": counts,
        }
    )

    color = "#A01236"

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
                    labelAngle=-45,  # Evita colisão nos valores de preço no mobile
                    labelFontSize=10,
                    titleFontSize=11,
                ),
            ),
            y=alt.Y(
                "count:Q",
                title="Days",
                axis=alt.Axis(
                    gridColor="#22272E",
                    domainColor="#444C56",
                    labelColor="#ADB5BD",
                    titleColor="#FFFFFF",
                    labelFontSize=10,
                    titleFontSize=11,
                ),
            ),
            tooltip=[
                alt.Tooltip("bin_start:Q", title="Bin Start", format="$.4f"),
                alt.Tooltip("bin_end:Q", title="Bin End", format="$.4f"),
                alt.Tooltip("count:Q", title="Days Count"),
            ],
        )
    )

    peg_line = (
        alt.Chart(pd.DataFrame([{"peg": 1.00}]))
        .mark_rule(color="#F6465D", strokeDash=[4, 4], strokeWidth=2)
        .encode(x="peg:Q")
    )

    chart = (
        (bars + peg_line)
        .properties(
            title=f"{symbol.upper()} Price Distribution",
            width="container",
            height=280,
            background="#0E1117",
        )
        .configure_title(anchor="start", color="#FFFFFF", fontSize=15)
        .configure_view(strokeWidth=0)
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

    total_circulating = df_grouped["circulating"].sum()
    df_grouped["pct"] = df_grouped["circulating"] / total_circulating

    domain = list(df_grouped["chain"])
    color_palette = {
        "Ethereum": "#627EEA",
        "Tron": "#FF0013",
        "Solana": "#14F195",
        "BSC": "#F3BA2F",
        "Hyperliquid L1": "#00AEE9",
        "Others": "#6E7681",
    }

    range_colors = [color_palette.get(chain, "#9E9E9E") for chain in domain]

    base = alt.Chart(df_grouped).encode(
        theta=alt.Theta("pct:Q", stack=True),
        color=alt.Color(
            "chain:N",
            title=None,
            scale=alt.Scale(domain=domain, range=range_colors),
            legend=alt.Legend(
                orient="bottom",
                direction="horizontal",
                columns=4,           # Quebra os itens em no máximo 4 colunas por linha
                symbolLimit=10,      # Garante a exibição de todos os itens
                labelColor="#FFFFFF",
                labelFontSize=10,
                padding=10           # Garante respiro entre o gráfico e a legenda
            ),
            sort=domain,
        ),
    )

    arcs = base.mark_arc(innerRadius=40, outerRadius=110).encode(
        tooltip=[
            alt.Tooltip("chain:N", title="Chain"),
            alt.Tooltip("pct:Q", title="Share", format=".1%"),
            alt.Tooltip(
                "circulating:Q", title="Circulating Supply", format="$,.0f"
            ),
        ]
    )

    labels = base.mark_text(
        radius=130, color="white", fontSize=11, fontWeight="bold"
    ).encode(text=alt.Text("pct:Q", format=".1%"))

    chart = (
        (arcs + labels)
        .properties(
            title="Top Chains by Circulating Stablecoins",
            width="container",
            height=360,  # Ligeiro aumento para dar respiro
            padding={"top": 30, "bottom": 10, "left": 10, "right": 10}, # Garante espaço em volta
            background="#0E1117",
        )
        .configure_title(
            anchor="middle",
            color="#FFFFFF",
            fontSize=15,
            dy=10  # Empurra o título levemente para DENTRO da área visível (evita o corte no topo)
        )
        .configure_view(strokeWidth=0)
    )
    return chart