import sqlite3
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
import scipy
import numpy as np
import altair as alt

database = "crypto_historical_data.db"
st.set_page_config(page_title="DashCrypto", layout="wide")


@st.cache_data
def load_crypto_data():
    with sqlite3.connect(database) as conn:
        df = pd.read_sql("SELECT time_close, close FROM btc_price", conn)
    return df

df = load_crypto_data()

@st.cache_resource
def generate_plot_log_regression(df):
    def fit_func(x, p1, p2, p3):
        return p1 + p2 * np.log(x) + p3 * np.log(x) ** 2
    
    
    def plot_adj_log_regression_btc(data_raw):
        data = data_raw.copy()
    
        # Data Sanitization
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
    
        # Calculate x_days (Day 1, 2, 3...)
        start_date = data["time_close"].min()
        data["x_days"] = (data["time_close"] - start_date).dt.days + 1
    
        # --- 1. Fair Value Calculation ---
        fitcut = (60, min(10 * 365, len(data)))
        cutdata = data.iloc[fitcut[0] : fitcut[1]]
        plotcutdata = data.iloc[fitcut[0] :].copy()
    
        popt_fv, _ = scipy.optimize.curve_fit(
            fit_func, cutdata["x_days"].values, np.log(cutdata["close"].values)
        )
    
        # FIX #1: Assign the exponentiated predictions to DataFrame columns
        polyfit_1d = fit_func(plotcutdata["x_days"].values, *popt_fv)
        plotcutdata["Fair Value"] = np.exp(polyfit_1d)
    
        # --- 2. Global Tops (Overvalued Data) ---
        tops = ("2011-06-08", "2013-11-30", "2017-12-16", "2021-04-14")
        top_dates = [pd.to_datetime(t).date() for t in tops]
        topcutdata = data[data["time_close"].dt.date.isin(top_dates)].copy()
    
        popt_top, _ = scipy.optimize.curve_fit(
            fit_func, topcutdata["x_days"].values, np.log(topcutdata["close"].values)
        )
    
        top_polyfit_1d = fit_func(plotcutdata["x_days"].values, *popt_top)
        plotcutdata["Overvalued"] = np.exp(top_polyfit_1d)
    
        # --- 3. Non-Bubble Data (Support ranges) ---
        nonbubble = [
            "2010-09-10",
            "2011-01-10",
            "2011-10-19",
            "2012-10-16",
            "2015-01-15",
            "2016-11-14",
            "2018-12-01",
            "2019-05-01",
            "2022-07-01",
            "2023-10-01",
        ]
    
        nonbubblepoints = []
        for i in range(len(nonbubble) // 2):
            s_date = pd.to_datetime(nonbubble[i * 2]).date()
            e_date = pd.to_datetime(nonbubble[i * 2 + 1]).date()
            curdata = data[
                (data["time_close"].dt.date >= s_date)
                & (data["time_close"].dt.date <= e_date)
            ]
            nonbubblepoints.append(curdata)
    
        nonbubblecutdata = pd.concat(nonbubblepoints)
    
        popt_nb, _ = scipy.optimize.curve_fit(
            fit_func,
            nonbubblecutdata["x_days"].values,
            np.log(nonbubblecutdata["close"].values),
        )
    
        nb_polyfit_1d = fit_func(plotcutdata["x_days"].values, *popt_nb)
        plotcutdata["Non-Bubble"] = np.exp(nb_polyfit_1d)
    
        # --- Legend Color Scale ---
        legend_domain = [
            "BTC Price",
            "Fair Value",
            "Overvalued (Tops)",
            "Non-Bubble (Support)",
        ]
        legend_range = ["#7FFFD4", "#FFFF00", "#FF0000", "#00FF00"]
    
        color_scale = alt.Color(
            "legend:N",
            scale=alt.Scale(domain=legend_domain, range=legend_range),
            legend=alt.Legend(
                title="Model Traces",
                orient="bottom-right",
                fillColor="#0e1117",
                strokeColor="#333333",
                padding=10,
                cornerRadius=5,
                labelColor="#cccccc",
                titleColor="#ffffff",
            ),
        )

        # --- Build Chart Traces using alt.datum() for legend binding ---
        base_line = alt.Chart(data[["time_close", "close"]]).mark_line(
            strokeWidth=1.5
        )
        fv_line = alt.Chart(plotcutdata[["time_close", "Fair Value"]]).mark_line(
            strokeWidth=2
        )
        top_line = alt.Chart(plotcutdata[["time_close", "Overvalued"]]).mark_line(
            strokeWidth=2
        )
        top_dots = alt.Chart(topcutdata[["time_close", "close"]]).mark_circle(
            color="#FF4500", size=60
        )
        nb_line = alt.Chart(plotcutdata[["time_close", "Non-Bubble"]]).mark_line(
            strokeWidth=2
        )
        nb_dots = alt.Chart(nonbubblecutdata[["time_close", "close"]]).mark_circle(
            color="#00FF00", size=30
        )
    
        # --- Combine Chart Layers ---
        chart = (
            alt.layer(
                base_line.encode(
                    x=alt.X(
                        "time_close:T",
                        title="Date",
                        axis=alt.Axis(gridColor="#222222", labelColor="#cccccc"),
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
                ).transform_calculate(legend="'BTC Price'"),
                fv_line.encode(
                    x="time_close:T",
                    y="Fair Value:Q",
                    color=color_scale,
                    tooltip=[
                        alt.Tooltip("time_close:T", title="Date"),
                        alt.Tooltip(
                            "Fair Value:Q", format="$,.2f", title="Fair Value"
                        ),
                    ],
                ).transform_calculate(legend="'Fair Value'"),
                top_line.encode(
                    x="time_close:T",
                    y="Overvalued:Q",
                    color=color_scale,
                    tooltip=[
                        alt.Tooltip("time_close:T", title="Date"),
                        alt.Tooltip(
                            "Overvalued:Q", format="$,.2f", title="Overvalued"
                        ),
                    ],
                ).transform_calculate(legend="'Overvalued (Tops)'"),
                top_dots.encode(
                    x="time_close:T",
                    y="close:Q",
                    tooltip=[
                        alt.Tooltip("time_close:T", title="Top Date"),
                        alt.Tooltip("close:Q", format="$,.2f", title="Top Price"),
                    ],
                ),
                nb_line.encode(
                    x="time_close:T",
                    y="Non-Bubble:Q",
                    color=color_scale,
                    tooltip=[
                        alt.Tooltip("time_close:T", title="Date"),
                        alt.Tooltip(
                            "Non-Bubble:Q", format="$,.2f", title="Non-Bubble"
                        ),
                    ],
                ).transform_calculate(legend="'Non-Bubble (Support)'"),
                nb_dots.encode(
                    x="time_close:T",
                    y="close:Q",
                    tooltip=[
                        alt.Tooltip("time_close:T", title="Support Date"),
                        alt.Tooltip(
                            "close:Q", format="$,.2f", title="Support Price"
                        ),
                    ],
                ),
            )
            .properties(
                height=700,
                title=alt.TitleParams(
                    text="Bitcoin Adjusted Logarithmic Regressions", color="white"
                ),
                background="#0e1117",
            )
            .configure_view(strokeWidth=0)
            .interactive()
        )
    
        return chart
    return plot_adj_log_regression_btc(df)

col1, col2 = st.columns(2)
with col1:
    fig = generate_plot_log_regression(df)
    st.altair_chart(fig)