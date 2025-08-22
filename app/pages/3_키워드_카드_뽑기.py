# pages/3_키워드_카드_뽑기.py
import streamlit as st
import random

st.set_page_config(page_title="키워드 카드 뽑기", layout="wide")
st.title("🃏 키워드 카드 뽑기")
st.caption("여러 키워드 중 일부를 무작위로 선택합니다. 각 키워드 버튼을 누르면 해당 카드만 다시 뽑습니다.")

st.markdown("""
<style>
div[data-testid="stButton"] > button {
    padding-top: 20px;
    padding-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if 'selected_keywords' not in st.session_state:
    st.session_state.selected_keywords = []
if 'all_keywords' not in st.session_state:
    st.session_state.all_keywords = []

keywords_input = st.text_area(
    "키워드 목록 (한 줄에 하나씩 입력)",
    "고양이\n강아지\n귀여운\n재미있는\n동물\n브이로그\n일상",
    height=200,
)
num_to_select = st.number_input("선택할 키워드 개수", min_value=1, value=3, step=1)

if st.button("키워드 뽑기", use_container_width=True):
    if keywords_input:
        all_keywords = [line.strip() for line in keywords_input.split('\n') if line.strip()]
        st.session_state.all_keywords = all_keywords
        if len(all_keywords) < num_to_select:
            st.warning("입력된 키워드 개수보다 더 많이 선택할 수 없습니다.")
            st.session_state.selected_keywords = []
        else:
            st.session_state.selected_keywords = random.sample(all_keywords, int(num_to_select))
    else:
        st.warning("키워드를 입력해주세요.")
        st.session_state.selected_keywords = []

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
    st.success("완료! 위의 텍스트를 복사해서 사용하세요.")
