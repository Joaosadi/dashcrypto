import requests
import streamlit as st


@st.cache_data
def get_snapshot():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,tether,usd-coin&vs_currencies=usd&include_24hr_change=true"
    r = requests.get(url)
    data = r.json()
    return data

@st.cache_data
def fetch_global_market_metrics():
    """Fetches total market cap, 24h change, 24h volume, and BTC dominance."""
    url = "https://api.coingecko.com/api/v3/global"
    try:
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()["data"]

        total_mcap = data["total_market_cap"]["usd"]
        mcap_change_24h = data["market_cap_change_percentage_24h_usd"]
        total_volume = data["total_volume"]["usd"]
        btc_dominance = data["market_cap_percentage"]["btc"]

        # Utility to format large dollar numbers ($2.45T, $75.20B)
        def format_currency(val):
            if val >= 1e12:
                return f"${val / 1e12:.2f}T"
            elif val >= 1e9:
                return f"${val / 1e9:.2f}B"
            return f"${val:,.0f}"

        return {
            "total_mcap": format_currency(total_mcap),
            "mcap_change": f"{mcap_change_24h:.2f}%",
            "mcap_change_raw": mcap_change_24h,
            "total_volume": format_currency(total_volume),
            "btc_dominance": f"{btc_dominance:.1f}%",
        }
    except Exception as e:
        # st.write(e)
        # Fallback values
        return {
            "total_mcap": "$--",
            "mcap_change": "0.00%",
            "mcap_change_raw": 0.0,
            "total_volume": "$--",
            "btc_dominance": "0.0%",
        }