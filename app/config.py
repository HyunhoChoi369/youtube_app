# lib/config.py
import streamlit as st

KEYS = ["PEXELS_KEY", "PIXABAY_KEY", "YOUTUBE_API_KEY"]
ENDPOINT_KEY = "YT_SEARCH_ENDPOINT"

def get(key: str) -> str:
    return st.session_state.get(key) or st.secrets.get(key, "") or ""
