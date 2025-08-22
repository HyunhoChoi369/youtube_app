# pages/3_Metadata_Formatter.py
import streamlit as st

st.set_page_config(page_title="키워드 카드 뽑기", layout="wide")
st.title("🃏 키워드 카드 뽑기")
st.caption("여러 키워드 중 일부를 무작위로 선택합니다.")

keywords_input = st.text_area(
    "키워드 목록 (한 줄에 하나씩 입력)",
    "고양이\n강아지\n귀여운\n재미있는\n동물\n브이로그\n일상",
    height=200,
)
num_to_select = st.number_input("선택할 키워드 개수", min_value=1, value=3, step=1)

if st.button("키워드 뽑기", use_container_width=True):
    if keywords_input:
        keywords = [line.strip() for line in keywords_input.split('\n') if line.strip()]
        if len(keywords) < num_to_select:
            st.warning("입력된 키워드 개수보다 더 많이 선택할 수 없습니다.")
        else:
            import random
            selected_keywords = random.sample(keywords, int(num_to_select))
            st.subheader("✨ 선택된 키워드:")
            st.code('\n'.join(selected_keywords), language="text")
            st.success("완료! 복사해서 사용하세요.")
    else:
        st.warning("키워드를 입력해주세요.")