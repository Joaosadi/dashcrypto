import sqlite3
import pandas as pd
import streamlit as st

from plots import btcregressionplots as btcplot
from plots import btcreturns as btcr
from plots import btcvolatilityplots as btcvol
from plots import stablecoinsplot as stbl
from plots import metrics as mt
from plots import macroplots as macrop

database = "crypto_historical_data.db"

def load_css(file_path="style.css"):
    try:
        with open(file_path, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

st.set_page_config(page_title="DashCrypto", layout="wide")
load_css()

# Header Title Banner
st.markdown(
    """
    <div class="title-banner">
        <h1>Crypto Market Quantitative Dashboard</h1>
        <p>Technical indicators, Models, and Statistical Analysis</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Snapshot Metrics - 3 colunas por linha funcionam melhor que 6 espremidas
marketsnap = mt.get_snapshot()
macro_data = mt.fetch_global_market_metrics()

row1_1, row1_2, row1_3 = st.columns(3)
with row1_1:
    st.metric(
        label="Bitcoin",
        value=f"${marketsnap['bitcoin']['usd']:,.0f}",
        delta=f"{marketsnap['bitcoin']['usd_24h_change']:.2f}%",
    )
with row1_2:
    st.metric(label="Total Market Cap", value=macro_data["total_mcap"], delta=macro_data["mcap_change"])
with row1_3:
    st.metric(label="24h Trading Volume", value=macro_data["total_volume"], delta="Global CEX/DEX", delta_color="off")

row2_1, row2_2, row2_3 = st.columns(3)
with row2_1:
    st.metric(label="Bitcoin Dominance", value=macro_data["btc_dominance"], delta="BTC Share", delta_color="off")
with row2_2:
    st.metric(label="USDT", value=f"${marketsnap['tether']['usd']:.4f}", delta=f"{marketsnap['tether']['usd_24h_change']:.2f}%")
with row2_3:
    st.metric(label="USDC", value=f"${marketsnap['usd-coin']['usd']:.4f}", delta=f"{marketsnap['usd-coin']['usd_24h_change']:.2f}%")

# Tabs
tab1, tab2, tab3 = st.tabs(["BTC Price Metrics", "Stablecoins", "Macro Metrics"])

@st.cache_data
def load_crypto_data():
    with sqlite3.connect(database) as conn:
        price_df = pd.read_sql("SELECT time_close, close, high, low FROM btc_price", conn)
    return price_df

df = load_crypto_data()
df["time_close"] = pd.to_datetime(df["time_close"], utc=True, format='mixed')
btc_price_df = df

with tab1:
    st.subheader("Price Regression Metrics")
    fig = btcplot.generate_plot_log_regression(df)
    st.altair_chart(fig, use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.altair_chart(btcplot.plot_log_regression_rainbow_btc(df), use_container_width=True)
    with col2:
        st.altair_chart(btcplot.plot_log_regression_btc_diff(df), use_container_width=True)

    st.subheader("Returns Metrics")
    col1, col2 = st.columns(2)
    with col1:
        nyears = st.slider("Number of years", min_value=1, max_value=7, value=1, step=1)
        st.altair_chart(btcr.n_year_returns(df, nyears), use_container_width=True)
    with col2:
        st.altair_chart(btcr.plot_returns_t_distribution(df), use_container_width=True)

    st.subheader("Volatility Metrics")
    col1, col2 = st.columns(2)
    with col1:
        st.altair_chart(btcvol.plot_btc_volatility(df), use_container_width=True)
    with col2:
        st.altair_chart(btcvol.plot_rvi(df), use_container_width=True)

    st.altair_chart(btcvol.plot_btc_volatility_bands(df), use_container_width=True)

with tab2:
    df_stables = stbl.get_stablecoin_circulating_data()
    prepared_data = stbl.prepare_top_stablecoin_data(df_stables)
    stablecoininchains = stbl.get_stablecoinchains()

    cols = st.columns(3)
    with cols[0]:
        st.metric(label="Total Marketcap", value=f"${stbl.get_stablecoin_marketcap(stablecoininchains)/1e9:,.1f} B")
    with cols[1]:
        st.metric(label="ETH Dominance", value=f"{stbl.get_ethereum_stablecoin_dominance(stablecoininchains)*100:.1f} %")
    with cols[2]:
        st.metric(label="Tether Dominance", value=f"{stbl.get_tether_dominance(df_stables)*100:.1f} %")

    st.subheader("Market Dominance")
    chart_type = st.radio(label="Display Mode", options=["Absolute Value ($B)", "Percentage Share (%)"], horizontal=True)
    fig = stbl.plot_stablecoin_historical_circulating(prepared_data, normalize=(chart_type == "Percentage Share (%)"))
    st.altair_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.altair_chart(stbl.plot_chain_stablecoin_dominance(stablecoininchains), use_container_width=True)
    with col2:
        st.altair_chart(stbl.plot_stablecoins_market_dominance(df_stables, nstables=6), use_container_width=True)

    st.subheader("Price Histograms x Peg")
    stablenames = ["usd-coin", "dai", "tether", "usds", "usd1-wlfi", 'ethena-usde']
    stablecoinprices = stbl.get_stablecoin_prices()

    # 2 colunas por linha garantem leitura sem espremer os histogramas no mobile
    for i in range(0, len(stablenames), 2):
        c1, c2 = st.columns(2)
        with c1:
            st.altair_chart(stbl.plot_stablecoin_price_histograms(stablecoinprices, symbol=stablenames[i]), use_container_width=True)
        if i + 1 < len(stablenames):
            with c2:
                st.altair_chart(stbl.plot_stablecoin_price_histograms(stablecoinprices, symbol=stablenames[i+1]), use_container_width=True)

with tab3:
    st.subheader("Macro Indicators vs Bitcoin Price")
    macro = macrop.fetch_fred_macro_data(start_date="2006-01-01", end_date=None)
    merged = macrop.merge_btc_with_macro(btc_price_df, macro)

    weekly = merged.resample("W").agg({
        "dxy": "last",
        "us_10y_yield": "last",
        "fed_balance_sheet": "last",
        "yield_curve_slope": "last",
        "btc_close": "last",
    }).dropna()

    charts = macrop.create_all_indicator_charts(weekly)
    items = list(charts.items())

    # Organiza em 2 colunas para Desktop (o CSS empilhará no celular)
    for i in range(0, len(items), 2):
        col1, col2 = st.columns(2)
        with col1:
            st.altair_chart(items[i][1], use_container_width=True)
        if i + 1 < len(items):
            with col2:
                st.altair_chart(items[i+1][1], use_container_width=True)

# Custom Footer
st.markdown(
    """
    <div class="custom-footer">
        <span>Analytics Dashboard • Built with Streamlit & Altair • v0.0.1</span>
    </div>
    """,
    unsafe_allow_html=True,
)