import pandas as pd
import streamlit as st
import scipy
import numpy as np
import altair as alt


# Default Global Setup
alt.data_transformers.disable_max_rows()
alt.themes.enable("dark")

def fit_func(x, p1, p2, p3):
    return p1 + p2 * np.log(x) + p3 * np.log(x) ** 2

fitcut = (60, -3 * 365)

# adjusted log regressions chart
@st.cache_resource
def generate_plot_log_regression(df):
    data = df.copy()

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

    cutdata = data.iloc[fitcut[0] : fitcut[1]]
    plotcutdata = data.iloc[fitcut[0] :].copy()

    popt_fv, _ = scipy.optimize.curve_fit(
        fit_func, cutdata["x_days"].values, np.log(cutdata["close"].values)
    )

    #1: Assign the exponentiated predictions to DataFrame columns
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
    )

    return chart



# rainbow regression
@st.cache_resource
def plot_log_regression_rainbow_btc(data_raw):
    data = data_raw.copy(deep=True)

    # 1. Clean date and close price columns
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

    # 2. Compute exact elapsed calendar days for regression
    start_date = data["time_close"].min()
    data["x_days"] = (data["time_close"] - start_date).dt.days + 1

    # 3. Fair value slicing
    cutdata = data.iloc[fitcut[0] : fitcut[1]]
    plotcutdata = data.iloc[fitcut[0] :]

    popt, _ = scipy.optimize.curve_fit(
        fit_func,
        cutdata["x_days"].values,
        np.log(cutdata["close"].values),
    )

    polyfit_1d = fit_func(plotcutdata["x_days"].values, *popt)
    plotcutdata["Log Regression"] = np.exp(polyfit_1d)

    # 5. Build Rainbow Bands Data
    nareas = 8
    # Plasma color palette matching previous theme dark gradient
    plasma_colors = [
        "#0d0887",
        "#46039f",
        "#7201a8",
        "#9c179e",
        "#bd3786",
        "#d8576b",
        "#ed7953",
        "#fb9f3a",
    ]

    band_charts = []
    for idx, i in enumerate(range(-2, nareas - 2)):
        band_df = plotcutdata[["time_close"]].copy()
        band_df["lower"] = np.exp(polyfit_1d + i / 2)
        band_df["upper"] = np.exp(polyfit_1d + (i + 1) / 2)

        band_chart = (
            alt.Chart(band_df)
            .mark_area(opacity=0.75, color=plasma_colors[idx])
            .encode(
                x="time_close:T",
                y="lower:Q",
                y2="upper:Q",
            )
        )
        band_charts.append(band_chart)

    # 6. Master Legend Scale (Standardized Palette)
    legend_domain = ["BTC Price", "Fit Data Segment", "Log Regression"]
    legend_range = ["#7FFFD4", "#6A5ACD", "#FFFF00"]

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

    # 7. Chart Traces
    base_price = (
        alt.Chart(data[["time_close", "close"]])
        .mark_line(strokeWidth=1.5)
        .encode(
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
        )
        .transform_calculate(legend="'BTC Price'")
    )

    fit_segment = (
        alt.Chart(cutdata[["time_close", "close"]])
        .mark_line(strokeWidth=2.5)
        .encode(
            x="time_close:T",
            y="close:Q",
            color=color_scale,
            tooltip=[
                alt.Tooltip("time_close:T", title="Date"),
                alt.Tooltip("close:Q", format="$,.2f", title="Fit Segment"),
            ],
        )
        .transform_calculate(legend="'Fit Data Segment'")
    )

    log_reg_line = (
        alt.Chart(plotcutdata[["time_close", "Log Regression"]])
        .mark_line(strokeWidth=2)
        .encode(
            x="time_close:T",
            y="Log Regression:Q",
            color=color_scale,
            tooltip=[
                alt.Tooltip("time_close:T", title="Date"),
                alt.Tooltip(
                    "Log Regression:Q",
                    format="$,.2f",
                    title="Fair Value Reg",
                ),
            ],
        )
        .transform_calculate(legend="'Log Regression'")
    )

    # 8. Layer Bands & Lines with Master Layout
    chart = (
        alt.layer(
            *band_charts,
            base_price,
            fit_segment,
            log_reg_line,
        )
        .properties(
            height=700,
            title=alt.TitleParams(
                text="Bitcoin Logarithm Regression Rainbows",
                color="white",
                fontSize=20,
            ),
            background="#0e1117",
        )
        .configure_view(strokeWidth=0)
    )

    return chart



# log regression difference

def plot_log_regression_btc_diff(data_raw):
    data = data_raw.copy(deep=True)

    # Clean data
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

    start_date = data["time_close"].min()
    data["x_days"] = (data["time_close"] - start_date).dt.days + 1

    cutdata = data.iloc[fitcut[0] : fitcut[1]]
    plotcutdata = data.iloc[fitcut[0] :].copy()

    def fit_func(x, p1, p2, p3):
        return p1 + p2 * np.log(x) + p3 * np.log(x) ** 2

    popt, _ = scipy.optimize.curve_fit(
        fit_func,
        cutdata["x_days"].values,
        np.log(cutdata["close"].values),
    )

    polyfit_1d = fit_func(plotcutdata["x_days"].values, *popt)
    plotcutdata["Log Regression"] = np.exp(polyfit_1d)

    plotcutdata["diff_ratio"] = (
        plotcutdata["close"] / plotcutdata["Log Regression"]
    )
    plotcutdata["diff_pct"] = plotcutdata["diff_ratio"] * 100

    legend_domain = [
        "BTC Price",
        "Fit Data Segment",
        "Log Regression",
        "Relative Ratio",
    ]
    legend_range = ["#7FFFD4", "#6A5ACD", "#FFFF00", "#FFA500"]

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

    # 1. Top Chart
    base_price = (
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
    )

    fit_segment = (
        alt.Chart(cutdata[["time_close", "close"]])
        .mark_line(strokeWidth=2.5)
        .encode(
            x="time_close:T",
            y="close:Q",
            color=color_scale,
            tooltip=[
                alt.Tooltip("time_close:T", title="Date"),
                alt.Tooltip("close:Q", format="$,.2f", title="Fit Segment"),
            ],
        )
        .transform_calculate(legend="'Fit Data Segment'")
    )

    log_reg_line = (
        alt.Chart(plotcutdata[["time_close", "Log Regression"]])
        .mark_line(strokeWidth=2)
        .encode(
            x="time_close:T",
            y="Log Regression:Q",
            color=color_scale,
            tooltip=[
                alt.Tooltip("time_close:T", title="Date"),
                alt.Tooltip(
                    "Log Regression:Q",
                    format="$,.2f",
                    title="Fair Value Reg",
                ),
            ],
        )
        .transform_calculate(legend="'Log Regression'")
    )

    top_chart = alt.layer(base_price, fit_segment, log_reg_line).properties(
        width=900, height=380
    )

    # 2. Bottom Chart
    ratio_line = (
        alt.Chart(plotcutdata[["time_close", "diff_ratio", "diff_pct"]])
        .mark_line(strokeWidth=1.5)
        .encode(
            x=alt.X(
                "time_close:T",
                title="Date",
                axis=alt.Axis(gridColor="#222222", labelColor="#cccccc"),
            ),
            y=alt.Y(
                "diff_ratio:Q",
                scale=alt.Scale(type="log"),
                title="Ratio to Regr.",
                axis=alt.Axis(gridColor="#222222", labelColor="#cccccc"),
            ),
            color=color_scale,
            tooltip=[
                alt.Tooltip("time_close:T", title="Date"),
                alt.Tooltip(
                    "diff_ratio:Q", format=".2f", title="Ratio Multiplier"
                ),
                alt.Tooltip("diff_pct:Q", format=".0f", title="% of Regr."),
            ],
        )
        .transform_calculate(legend="'Relative Ratio'")
    )

    baseline = (
        alt.Chart(pd.DataFrame({"y": [1.0]}))
        .mark_rule(color="#ffffff", strokeDash=[4, 4], opacity=0.5)
        .encode(y="y:Q")
    )

    bottom_chart = alt.layer(baseline, ratio_line).properties(
        width=900, height=180
    )

    # 3. Concatenate
    combined_chart = (
        alt.vconcat(top_chart, bottom_chart)
        .resolve_scale(x="shared")
        .properties(
            title=alt.TitleParams(
                text="Bitcoin Fair Value Logarithm Regression & Difference Ratio",
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