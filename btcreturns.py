import sqlite3
import pandas as pd
import streamlit as st
import scipy
import numpy as np
import altair as alt
import scipy.stats as stats

@st.cache_resource
def n_year_returns(data_raw, n):
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

    # Calculate n-year log10 returns: log10(1 + pct_change)
    data["returns"] = np.log10(1 + data["close"].pct_change(int(365 * n)))

    # Master legend scale
    legend_domain = ["BTC Price", f"{n}-Year Return (log10)"]
    legend_range = ["#7FFFD4", "#0000FF"]  # Aquamarine & Blue

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

    # 1. Top Chart - BTC Price (Log Scale)
    top_chart = (
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
        .properties(width=900, height=380)
    )

    # 2. Bottom Chart - Returns
    bottom_chart = (
        alt.Chart(data.dropna(subset=["returns"])[["time_close", "returns"]])
        .mark_line(strokeWidth=1.5)
        .encode(
            x=alt.X(
                "time_close:T",
                title="Date",
                axis=alt.Axis(gridColor="#222222", labelColor="#cccccc"),
            ),
            y=alt.Y(
                "returns:Q",
                title=f"{n}-Yr Log10 Return",
                axis=alt.Axis(gridColor="#442222", labelColor="#cccccc"),
            ),
            color=color_scale,
            tooltip=[
                alt.Tooltip("time_close:T", title="Date"),
                alt.Tooltip(
                    "returns:Q", format=".3f", title=f"{n}-Yr Log Return"
                ),
            ],
        )
        .transform_calculate(legend=f"'{n}-Year Return (log10)'")
        .properties(width=900, height=180)
    )

    # 3. Concatenate vertically
    combined_chart = (
        alt.vconcat(top_chart, bottom_chart)
        .resolve_scale(x="shared")
        .properties(
            title=alt.TitleParams(
                text=f"Bitcoin {n}-Year Log10 Returns",
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

@st.cache_resource
def plot_returns_t_distribution(df_raw):
    data = df_raw.copy()

    # 1. Clean data and compute daily percent returns
    data["close"] = pd.to_numeric(
        data["close"].astype(str).str.replace("$", "").str.replace(",", ""),
        errors="coerce",
    )
    returns = data["close"].pct_change(1).dropna().values

    # 2. Compute 95% Confidence Interval (2.5th and 97.5th percentiles)
    ci_lower, ci_upper = np.percentile(returns, [2.5, 97.5])

    # 3. Fit Student's t-distribution
    df_param, loc_param, scale_param = stats.t.fit(returns)

    # 4. Generate fitted PDF points
    x_eval = np.linspace(returns.min(), returns.max(), 500)
    pdf_eval = stats.t.pdf(x_eval, df_param, loc_param, scale_param)
    pdf_df = pd.DataFrame({"returns": x_eval, "density": pdf_eval})

    returns_df = pd.DataFrame({"returns": returns})
    ci_df = pd.DataFrame({"ci_val": [ci_lower, ci_upper]})

    # 5. Master Legend Color Scale
    color_scale = alt.Color(
        "legend:N",
        scale=alt.Scale(
            domain=["Daily Returns", "Fitted Student-t", "95% CI Bounds"],
            range=["#7FFFD4", "#3F51B5", "#FF4500"],  # Aquamarine, Gold, Orange-Red
        ),
        legend=alt.Legend(
            title="Model Traces",
            orient="top-right",
            fillColor="#0e1117",
            strokeColor="#333333",
            padding=8,
            cornerRadius=5,
            labelColor="#cccccc",
            titleColor="#ffffff",
        ),
    )

    # 6. Frequency Histogram Layer
    histogram = (
        alt.Chart(returns_df)
        .mark_bar(opacity=0.85)
        .encode(
            x=alt.X(
                "returns:Q",
                bin=alt.Bin(maxbins=100),
                title="Daily Return",
                axis=alt.Axis(
                    format="%", gridColor="#222222", labelColor="#cccccc"
                ),
            ),
            y=alt.Y(
                "count()",
                title="Frequency (Days)",
                axis=alt.Axis(gridColor="#222222", labelColor="#cccccc"),
            ),
            color=color_scale,
            tooltip=[
                alt.Tooltip(
                    "returns:Q",
                    bin=True,
                    format=".2%",
                    title="Return Bin Range",
                ),
                alt.Tooltip("count()", title="Days Count"),
            ],
        )
        .transform_calculate(legend="'Daily Returns'")
    )

    # 7. Fitted Student's t PDF Line Layer
    t_curve = (
        alt.Chart(pdf_df)
        .mark_line(strokeWidth=2.5)
        .encode(
            x="returns:Q",
            y=alt.Y("density:Q", axis=None),
            color=color_scale,
            tooltip=[
                alt.Tooltip("returns:Q", format=".2%", title="Return"),
                alt.Tooltip("density:Q", format=".2f", title="Model Density"),
            ],
        )
        .transform_calculate(legend="'Fitted Student-t'")
    )

    # 8. Vertical 95% Confidence Interval Dashed Lines Layer
    ci_lines = (
        alt.Chart(ci_df)
        .mark_rule(strokeDash=[6, 6], strokeWidth=2)
        .encode(
            x="ci_val:Q",
            color=color_scale,
            tooltip=[
                alt.Tooltip("ci_val:Q", format=".2%", title="95% CI Boundary")
            ],
        )
        .transform_calculate(legend="'95% CI Bounds'")
    )

    # 9. Combine Layers
    chart = (
        alt.layer(histogram, t_curve, ci_lines)
        .resolve_scale(y="independent")
        .properties(
            width=900,
            height=480,
            title=alt.TitleParams(
                text="Bitcoin Daily Returns Distribution with 95% Confidence Interval",
                subtitle=(
                    f"95% CI: [{ci_lower:.2%}, {ci_upper:.2%}] | "
                    f"Student's t (ν={df_param:.2f}, loc={loc_param:.4f}, scale={scale_param:.4f})"
                ),
                color="white",
                subtitleColor="#aaaaaa",
                fontSize=18,
                anchor="start",
            ),
            background="#0e1117",
        )
        .configure_view(strokeWidth=0)
    )

    return chart


