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

        st.header("🌐 서비스 엔드포인트")
        default_ep = get(ENDPOINT_KEY) or "https://search-youtube-417935223154.europe-west1.run.app/search-shorts"
        ep = st.text_input("YouTube Shorts Search API", value=default_ep, help="Cloud Run 엔드포인트")
        st.session_state[ENDPOINT_KEY] = ep
