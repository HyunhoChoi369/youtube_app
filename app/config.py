# lib/config.py
import streamlit as st

KEYS = ["PEXELS_KEY", "PIXABAY_KEY", "YOUTUBE_API_KEY"]
ENDPOINT_KEY = "YT_SEARCH_ENDPOINT"


def get(key: str) -> str:
    return st.session_state.get(key) or st.secrets.get(key, "") or ""

def render_key_inputs():
    with st.sidebar:
        st.header("🔐 API Keys")
        for k in KEYS:
            label = k.replace("_", " ").title()
            val = st.text_input(label, value=get(k), type="password")
            st.session_state[k] = val
