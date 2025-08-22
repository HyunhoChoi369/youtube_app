# pages/3_키워드_카드_뽑기.py
import streamlit as st
import random
import os

st.set_page_config(page_title="키워드 카드 뽑기", layout="wide")
st.title("🃏 키워드 카드 뽑기")
st.caption("키워드 파일에서 무작위로 선택합니다. 각 키워드 버튼을 누르면 해당 카드만 다시 뽑습니다.")

st.markdown("""
<style>
div[data-testid="stButton"] > button {
    padding-top: 20px;
    padding-bottom: 20px;
    font-size: 20px;
}
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if 'selected_keywords' not in st.session_state:
    st.session_state.selected_keywords = []
if 'all_keywords' not in st.session_state:
    st.session_state.all_keywords = []

@st.cache_data
def load_keywords(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        st.error(f"파일을 찾을 수 없습니다: {file_path}")
        return []

# 키워드 파일 경로
keyword_file = os.path.join(os.path.dirname(__file__), "..", "keywords.txt")
all_keywords = load_keywords(keyword_file)

if all_keywords:
    st.session_state.all_keywords = all_keywords
    
    col1, col2, spacer = st.columns([1,1,5])
    with col1:
        num_to_select = st.number_input("선택할 키워드 개수", min_value=1, value=3, step=1, label_visibility="collapsed")
    with col2:
        pick_button_pressed = st.button("키워드 뽑기", use_container_width=True)

    if pick_button_pressed:
        if len(all_keywords) < num_to_select:
            st.warning("키워드 파일의 키워드 개수보다 더 많이 선택할 수 없습니다.")
            st.session_state.selected_keywords = []
        else:
            st.session_state.selected_keywords = random.sample(all_keywords, int(num_to_select))

if st.session_state.selected_keywords:
    st.subheader("✨ 선택된 키워드:")
    
    cols = st.columns(len(st.session_state.selected_keywords))
    
    for i, keyword in enumerate(st.session_state.selected_keywords):
        with cols[i]:
            if st.button(keyword, key=f"keyword_{i}", use_container_width=True):
                remaining_keywords = [kw for kw in st.session_state.all_keywords if kw not in st.session_state.selected_keywords or kw == keyword]
                if remaining_keywords:
                    new_keyword = random.choice(remaining_keywords)
                    st.session_state.selected_keywords[i] = new_keyword
                    st.rerun()
                else:
                    st.warning("더 이상 새로운 키워드가 없습니다.")

    st.markdown("---")
    final_keywords = " ".join(st.session_state.selected_keywords)
    st.code(final_keywords, language="text")
    st.success("완료!")
else:
    if not all_keywords:
        st.warning("키워드 파일을 찾을 수 없거나 파일에 내용이 없습니다.")