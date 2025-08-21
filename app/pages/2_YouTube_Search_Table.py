# pages/2_YouTube_Search_Table.py
import json
import pandas as pd
import requests
import streamlit as st
import config, utils

st.set_page_config(page_title="YouTube 검색 시트", layout="wide")
st.title("📺 YouTube 검색 시트 (Cloud Run)")

config.render_key_inputs()
ENDPOINT = config.get("YT_SEARCH_ENDPOINT") or "https://search-youtube-417935223154.europe-west1.run.app/search-shorts"

# 세션 상태 준비
if "yt_results" not in st.session_state:
    st.session_state["yt_results"] = pd.DataFrame()

search_tab, sort_tab = st.tabs(["🔎 검색", "↕️ 정렬/랭킹"])

# =========================
# 🔎 검색 탭
# =========================
with search_tab:
    st.subheader("검색 옵션 (Cloud Run POST 호출)")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        keyword = st.text_input("keyword*", placeholder="예: debate, 국회 본회의, economy")
    with c2:
        days = st.number_input("days", min_value=1, max_value=30, value=7, step=1)
    with c3:
        max_results = st.number_input("max_results", min_value=1, max_value=200, value=100, step=1)
    with c4:
        top_n = st.number_input("top_n", min_value=1, max_value=50, value=10, step=1)
    with c5:
        rank_by = st.selectbox("rank_by", ["score","view_count","views_per_hour","like_count","likes_per_view"], index=0)
    with c6:
        fmt = st.selectbox("format", ["json","values"], index=0)

    run = st.button("검색 실행", type="primary", use_container_width=True)

    if run:
        if not keyword.strip():
            st.warning("keyword는 필수입니다.")
        else:
            payload = {
                "keyword": keyword.strip(),
                "days": int(days),
                "max_results": int(max_results),
                "top_n": int(top_n),
                "rank_by": rank_by,
                "format": fmt
            }
            with st.spinner("Cloud Run 호출 중..."):
                try:
                    resp = requests.post(ENDPOINT, json=payload, timeout=60)
                    resp.raise_for_status()
                    data = resp.json()
                    df = utils.df_from_service(data)           # json/values 모두 대응
                    df = utils.normalize_youtube_df(df)        # 시간/숏츠 플래그 등
                    df = utils.ensure_url_columns(df)          # videoId → url
                    df = utils.standardize_cols(df)            # view_count→viewCount 등 공통 키 정렬
                    st.session_state["yt_results"] = df
                    st.success(f"총 {len(df)}행 로드 완료!")
                except requests.HTTPError as e:
                    st.error(f"HTTP {e.response.status_code}: {e.response.text[:500]}")
                except Exception as e:
                    st.error(f"요청/파싱 실패: {e}")

    st.divider()
    st.caption("현재 엔드포인트")
    st.code(ENDPOINT, language="text")

# =========================
# ↕️ 정렬/랭킹 탭
# =========================
with sort_tab:
    df = st.session_state["yt_results"].copy()
    if df.empty:
        st.info("데이터가 없습니다. 🔎 검색 탭에서 먼저 조회하세요.")
    else:
        st.subheader("정렬 규칙")
        left, right = st.columns([2,1])

        with left:
            cols = df.columns.tolist()
            default_primary = "publishedAt_local" if "publishedAt_local" in cols else cols[0]
            primary = st.selectbox("1차 정렬 컬럼", cols, index=cols.index(default_primary))
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
                w_short   = st.slider("가중치: 쇼츠(<=60s)", 0.0, 1.0, 0.2, 0.05)
                st.caption("※ 결측 컬럼은 0으로 계산됩니다.")

        if use_rank:
            df = utils.add_composite_score(df,
                                           w_recency=w_recency,
                                           w_views=w_views,
                                           w_likes=w_likes,
                                           w_short=w_short)

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
        colcfg = {}
        if "url" in df.columns:
            colcfg["url"] = st.column_config.LinkColumn("YouTube", display_text="열기")
        st.dataframe(df, use_container_width=True, height=520, column_config=colcfg)

        st.download_button(
            "CSV 다운로드",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="youtube_results_sorted.csv",
            mime="text/csv"
        )
