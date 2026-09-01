import requests
import streamlit as st


@st.cache_data
def get_snapshot():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,tether,usd-coin&vs_currencies=usd&include_24hr_change=true"
    r = requests.get(url, params=params)
    data = r.json()
    return data