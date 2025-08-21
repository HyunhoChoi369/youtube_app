# pages/2_YouTube_Search_Table.py
import json
import io
import pandas as pd
import streamlit as st
from lib import config, utils

st.set_page_config(page_title="YouTube 검색 시트", layout="wide")
st.title("📺 YouTube 검색 시트")
config.render_key_inputs()

# 세션 상태 준비
if "yt_results" not in st.session_state:
    st.session_state["yt_results"] = pd.DataFrame()

search_tab, sort_tab = st.tabs(["🔎 검색(훅/테스트 입력)", "↕️ 정렬/랭킹"])

# =========================
# 🔎 검색 탭 (API 호출은 네 함수로 연결)
# =========================
with search_tab:
    st.subheader("검색 옵션 (UI만 제공 — 실제 호출은 사용자 함수로)")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        q = st.text_input("키워드", placeholder="예: debate, 국회 본회의, economy")
    with col2:
        region = st.text_input("regionCode", value="KR")
    with col3:
        order = st.selectbox("order", ["relevance","date","viewCount","rating"], index=0)
    with col4:
        max_results = st.slider("maxResults", 5, 50, 25)

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        lang = st.text_input("relevanceLanguage", value="ko")
    with col6:
        duration = st.selectbox("videoDuration", ["any","short","medium","long"], index=0)
    with col7:
        safe = st.selectbox("safeSearch", ["none","moderate","strict"], index=1)
    with col8:
        st.write("")  # spacing
        run_btn = st.button("내 검색 함수로 실행(훅)", use_container_width=True)

    st.markdown("""
    **연결 방법:** 아래 형태로 만들어 둔 함수를 호출해서 `DataFrame`을 `st.session_state["yt_results"]`에 넣으면 표가 갱신됩니다.

    ```python
    # 예시: 네가 이미 만든 함수 사용 (여기서는 의사코드)
    # df = run_youtube_search(query=q, regionCode=region, order=order,
    #                         relevanceLanguage=lang, videoDuration=duration,
    #                         safeSearch=safe, maxResults=max_results)
    # st.session_state["yt_results"] = utils.ensure_url_columns(utils.normalize_youtube_df(df))
    ```

    - **필수 컬럼 권장:** `videoId`, `title`, `channelTitle`, `publishedAt`, *(가능하면)* `durationSec`, `viewCount`, `likeCount`, `thumbnail`
    - 없더라도 표시 가능하지만, 정렬/랭킹에서 가중치 계산은 제한될 수 있어요.
    """)

    if run_btn:
        st.info("여기서는 실제 API를 호출하지 않습니다. 위 코드블록처럼 당신의 함수에서 DataFrame을 넣어주세요.")

    st.divider()
    st.caption("🧪 테스트용 입력(실제 API 없이 결과를 미리 확인하려면)")
    test_col1, test_col2 = st.columns(2)
    with test_col1:
        raw_json = st.text_area("YouTube API 응답(JSON) 붙여넣기 또는 리스트 형태", height=220,
                                placeholder='{"items":[{"id":{"videoId":"abc"},"snippet":{...}}, ...]}  또는  [{"videoId":"...","title":"..."}]')
        apply_json = st.button("JSON 적용", use_container_width=True)
    with test_col2:
        uploaded = st.file_uploader("CSV/JSON 업로드", type=["csv","json"])
        apply_upload = st.button("업로드 적용", use_container_width=True)

    new_df = None
    if apply_json and raw_json.strip():
        try:
            data = json.loads(raw_json)
            # YouTube search 'items' or already flatted list 지원
            items = data.get("items", data if isinstance(data, list) else [])
            new_df = utils.df_from_youtube_items(items)
        except Exception as e:
            st.error(f"JSON 파싱 실패: {e}")

    if apply_upload and uploaded:
        try:
            if uploaded.name.lower().endswith(".csv"):
                new_df = pd.read_csv(uploaded)
            else:
                data = json.loads(uploaded.read().decode("utf-8"))
                items = data.get("items", data if isinstance(data, list) else [])
                new_df = utils.df_from_youtube_items(items)
        except Exception as e:
            st.error(f"업로드 파싱 실패: {e}")

    if new_df is not None:
        st.session_state["yt_results"] = utils.ensure_url_columns(utils.normalize_youtube_df(new_df))
        st.success(f"데이터 {len(st.session_state['yt_results'])}행 적용 완료!")

# =========================
# ↕️ 정렬/랭킹 탭 (시트 재정렬)
# =========================
with sort_tab:
    df = st.session_state["yt_results"].copy()
    if df.empty:
        st.info("아직 데이터가 없습니다. 🔎 검색 탭에서 결과를 주입하세요.")
    else:
        st.subheader("정렬 규칙")
        left, right = st.columns([2,1])

        with left:
            cols = df.columns.tolist()
            primary = st.selectbox("1차 정렬 컬럼", cols, index=cols.index("publishedAt_local") if "publishedAt_local" in cols else 0)
            primary_asc = st.checkbox("오름차순(1차)", value=False)

            secondary = st.selectbox("2차 정렬 컬럼(선택)", ["(없음)"] + cols, index=0)
            secondary_asc = st.checkbox("오름차순(2차)", value=True)
            apply_sort = st.button("정렬 적용", use_container_width=True)

        with right:
            st.markdown("**가중치 랭킹(선택)**")
            use_rank = st.checkbox("Composite Score 사용")
            if use_rank:
                w_recency = st.slider("가중치: 최신성", 0.0, 1.0, 0.4, 0.05)
                w_views   = st.slider("가중치: 조회수", 0.0, 1.0, 0.4, 0.05)
                w_likes   = st.slider("가중치: 좋아요", 0.0, 1.0, 0.2, 0.05)
                w_short   = st.slider("가중치: 쇼츠(<=60s) 선호", 0.0, 1.0, 0.2, 0.05)
                st.caption("※ 해당 컬럼이 없으면 해당 항목은 0으로 처리됩니다.")

        # 점수 계산
        if use_rank:
            df = utils.add_composite_score(df,
                                           w_recency=w_recency,
                                           w_views=w_views,
                                           w_likes=w_likes,
                                           w_short=w_short)

        # 정렬 적용
        if apply_sort:
            by_cols = [primary]
            asc_list = [primary_asc]
            if secondary != "(없음)":
                by_cols.append(secondary)
                asc_list.append(secondary_asc)
            if use_rank and "score" in df.columns:
                by_cols = ["score"] + by_cols
                asc_list = [False] + asc_list
            df = df.sort_values(by=by_cols, ascending=asc_list)

        st.subheader("결과 시트")
        # 링크 컬럼 설정
        colcfg = {}
        if "url" in df.columns:
            colcfg["url"] = st.column_config.LinkColumn("YouTube", display_text="열기")
        st.dataframe(df, use_container_width=True, height=500, column_config=colcfg)

        st.download_button("CSV 다운로드", data=df.to_csv(index=False).encode("utf-8"),
                           file_name="youtube_results_sorted.csv", mime="text/csv")
