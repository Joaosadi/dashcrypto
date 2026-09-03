import sqlite3
import pandas as pd
import streamlit as st

import btcregressionplots as btcplot
import btcreturns as btcr
import btcvolatilityplots as btcvol
import stablecoinsplot as stbl
import metrics as mt

database = "crypto_historical_data.db"

#function to load style.css
def load_css(file_path="style.css"):
    with open(file_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css()

st.set_page_config(page_title="DashCrypto", layout="wide")

#Header Title Banner
st.markdown(
    """
    <div class="title-banner">
        <h1>Crypto Market Quantitative Dashboard</h1>
        <p>Technical indicators, Models, and Statistical Analysis</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# snapshot metrics
marketsnap = mt.get_snapshot()
macro_data = mt.fetch_global_market_metrics()

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric(
        label="Bitcoin",
        value=f"${marketsnap['bitcoin']['usd']:,.0f}",
        delta=f"{marketsnap['bitcoin']['usd_24h_change']:.2f}%",
        delta_color="normal",
    )
    
with col2:
    st.metric(
        label="Total Market Cap",
        value=macro_data["total_mcap"],
        delta=macro_data["mcap_change"],
        delta_color="normal",
    )

with col3:
    st.metric(
        label="24h Trading Volume",
        value=macro_data["total_volume"],
        delta="Global CEX/DEX",
        delta_color="off",
    )

with col4:
    st.metric(
        label="Bitcoin Dominance",
        value=macro_data["btc_dominance"],
        delta="BTC Share of Total Cap",
        delta_color="off",
    )
    
with col5:
    st.metric(
        label="USDT",
        value=f"${marketsnap['tether']['usd']:.4f}",
        delta=f"{marketsnap['tether']['usd_24h_change']:.2f}%",
        delta_color="normal",
    )

with col6:
    st.metric(
        label="USDC",
        value=f"${marketsnap['usd-coin']['usd']:.4f}",
        delta=f"{marketsnap['usd-coin']['usd_24h_change']:.2f}%",
        delta_color="normal",
    )



# tabs
tab1, tab2 = st.tabs(["BTC price metrics", "Stablecoins"])

with tab1:

    @st.cache_data
    def load_crypto_data():
        with sqlite3.connect(database) as conn:
            df = pd.read_sql("SELECT time_close, close, high, low FROM btc_price", conn)
        return df
    
    df = load_crypto_data()
    df["time_close"] = pd.to_datetime(df["time_close"], utc=True, format='mixed')

    st.header("Price regression metrics")
    fig = btcplot.generate_plot_log_regression(df)
    st.altair_chart(fig, use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = btcplot.plot_log_regression_rainbow_btc(df)
        st.altair_chart(fig, use_container_width=True)


    
    with col2:
        fig = btcplot.plot_log_regression_btc_diff(df)
        st.altair_chart(fig, use_container_width=True)


    st.header("Returns metrics")

    col1, col2 = st.columns(2)
    
    with col1:
        nyears = st.slider("Number of years", min_value=1, max_value=7, value=1, step=1)
        fig = btcr.n_year_returns(df, nyears)
        st.altair_chart(fig, use_container_width=True)


    with col2:
        fig = btcr.plot_returns_t_distribution(df)
        st.altair_chart(fig, use_container_width=True)


    # volatility

    st.header("Volatility metrics")
    
    col1, col2 = st.columns(2)

    with col1:
        fig = btcvol.plot_btc_volatility(df)
        st.altair_chart(fig, use_container_width=True)

    with col2:
        fig = btcvol.plot_rvi(df)
        st.altair_chart(fig, use_container_width=True)

    fig = btcvol.plot_btc_volatility_bands(df)
    st.altair_chart(fig, use_container_width=True)


# stablecoins tabs

    with tab2:
        df = stbl.get_stablecoin_circulating_data()
        prepared_data = stbl.prepare_top_stablecoin_data(df)
        col1, col2 = st.columns(2)

        with col1:
            chart_type = st.radio(
                        label="Display Mode",
                        options=["Absolute Value ($B)", "Percentage Share (%)"],
                        horizontal=True,)
            fig = stbl.plot_stablecoin_historical_circulating(prepared_data, normalize = chart_type == "Percentage Share (%)")
            st.altair_chart(fig, use_container_width=True,theme=None)
        
        with col2:
            nstables = st.slider("Number of stablecoins", min_value=3, max_value = 10, value=5, step=1)
            fig = stbl.plot_stablecoins_market_dominance(df, nstables = nstables)
            st.altair_chart(fig, use_container_width=True)
    
# Custom Footer
st.markdown(
    """
    <div class="custom-footer">
        <span>Analytics Dashboard • Built with Streamlit & Altair • v0.0.1</span>
    </div>
    """,
    unsafe_allow_html=True,
)