import sqlite3
import pandas as pd
import streamlit as st

import btcregressionplots as btcplot
import btcreturns as btcr

database = "crypto_historical_data.db"
st.set_page_config(page_title="DashCrypto", layout="wide")


@st.cache_data
def load_crypto_data():
    with sqlite3.connect(database) as conn:
        df = pd.read_sql("SELECT time_close, close FROM btc_price", conn)
    return df

df = load_crypto_data()

tab1, tab2 = st.tabs(["BTC metrics", "Stablecoins"])

with tab1:

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