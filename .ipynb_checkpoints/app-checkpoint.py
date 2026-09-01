import sqlite3
import pandas as pd
import streamlit as st

import btcregressionplots as btcplot
import btcreturns as btcr
import btcvolatilityplots as btcvol
import stablecoinsplot as stbl

database = "crypto_historical_data.db"
st.set_page_config(page_title="DashCrypto", layout="wide")


# 2. Custom CSS for Title Banner, Card Styling, and Footer
st.markdown(
    """
    <style>
    /* Global Container Padding */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }
    
    /* Header Banner Styling */
    .title-banner {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
        padding: 24px 32px;
        border-radius: 12px;
        color: #ffffff;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        margin-bottom: 24px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .title-banner h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        color: #ffffff;
    }
    .title-banner p {
        margin: 6px 0 0 0;
        font-size: 1rem;
        color: #c7d2fe;
    }

    /* Footer Styling */
    .custom-footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #0e1117;
        color: #888888;
        text-align: center;
        padding: 8px 0;
        font-size: 0.85rem;
        border-top: 1px solid #222222;
        z-index: 999;
    }
    .custom-footer a {
        color: #8b5cf6;
        text-decoration: none;
        font-weight: 600;
    }
    .custom-footer a:hover {
        text-decoration: underline;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# 3. Header Title Banner
st.markdown(
    """
    <div class="title-banner">
        <h1>Crypto Market Quantitative Dashboard</h1>
        <p>Technical indicators, Models, and Statistical Analysis</p>
    </div>
""",
    unsafe_allow_html=True,
)

# daily snapshot metrics

# --- CUSTOM CSS FOR PROFESSIONAL KPI CARDS ---
st.markdown(
    """
    <style>
    .metric-container {
        display: flex;
        gap: 16px;
        margin-bottom: 24px;
    }
    .metric-card {
        background: #131722;
        border: 1px solid #2a2e39;
        border-radius: 10px;
        padding: 16px 20px;
        flex: 1;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        border-color: #434651;
        transform: translateY(-2px);
    }
    .metric-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .metric-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #848e9c;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-badge {
        font-size: 0.75rem;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 4px;
    }
    .badge-positive {
        background-color: rgba(14, 203, 129, 0.15);
        color: #0ecb81;
    }
    .badge-negative {
        background-color: rgba(246, 70, 93, 0.15);
        color: #f6465d;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #ffffff;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .metric-sub {
        font-size: 0.75rem;
        color: #5e6673;
        margin-top: 4px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

tab1, tab2 = st.tabs(["BTC price metrics", "Stablecoins"])

with tab1:

    @st.cache_data
    def load_crypto_data():
        with sqlite3.connect(database) as conn:
            df = pd.read_sql("SELECT time_close, close, high, low FROM btc_price", conn)
        return df
    
    df = load_crypto_data()

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