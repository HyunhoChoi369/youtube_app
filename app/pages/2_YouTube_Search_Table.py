# pages/2_YouTube_Search_Table.py
import json
import pandas as pd
import requests
import streamlit as st
import config, utils

st.set_page_config(page_title="YouTube 검색 시트 (Cloud Run)", layout="wide")
st.title("📺 YouTube 검색 시트 (Cloud Run)")

config.render_key_inputs()
ENDPOINT = config.get("YT_SEARCH_ENDPOINT") or "https://search-youtube-417935223154.europe-west1.run.app/search-shorts"

# -----------------------------
# 세션 상태 초기화
# -----------------------------
ss = st.session_state
if "yt_results_raw" not in ss:
    ss["yt_results_raw"] = pd.DataFrame()   # 원본(검색 결과)
if "yt_results_view" not in ss:
    ss["yt_results_view"] = pd.DataFrame()  # 정렬/필터 반영 뷰

# -----------------------------
# 탭: 검색 / 정렬
# -----------------------------
search_tab, sort_tab = st.tabs(["🔎 검색", "↕️ 정렬/랭킹"])

# ▼ 페이지 맨 아래 공용 표를 그릴 '앵커'
shared_table = st.container()

# === 🔎 검색 탭 ===
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

                    # 서비스 응답 → DF 정규화
                    df = utils.df_from_service(data)
                    df = utils.standardize_cols(df)
                    df = utils.normalize_youtube_df(df)
                    df = utils.ensure_url_columns(df)

                    ss["yt_results_raw"] = df
                    ss["yt_results_view"] = df.copy()  # 검색 직후엔 뷰 = 원본
                    st.success(f"총 {len(df)}행 로드 완료! 아래 공용 시트에서 확인하세요.")
                except requests.HTTPError as e:
                    st.error(f"HTTP {e.response.status_code}: {e.response.text[:500]}")
                except Exception as e:
                    st.error(f"요청/파싱 실패: {e}")

    st.caption("현재 엔드포인트")
    st.code(ENDPOINT, language="text")

# === ↕️ 정렬/랭킹 탭 ===
with sort_tab:
    base = ss["yt_results_raw"]
    if base.empty:
        st.info("데이터가 없습니다. 🔎 검색 탭에서 먼저 조회하세요.")
    else:
        st.subheader("정렬/랭킹 규칙 (아래 공용 시트에 즉시 반영)")
        left, right = st.columns([2,1])

        with left:
            cols = [c for c in base.columns.tolist() if c not in ("videoId", "url", "video_url")]
            default_primary = "publishedAt_local" if "publishedAt_local" in cols else cols[0]
            primary = st.selectbox("1차 정렬 컬럼", cols, index=cols.index(default_primary))
            primary_asc = st.checkbox("오름차순(1차)", value=False)

            secondary = st.selectbox("2차 정렬 컬럼(선택)", ["(없음)"] + cols, index=0)
            secondary_asc = st.checkbox("오름차순(2차)", value=True)

        with right:
            st.markdown("**가중치 랭킹(선택)**")
            use_rank = st.checkbox("Composite Score 사용")
            if use_rank:
                w_recency = st.slider("가중치: 최신성", 0.0, 1.0, 0.4, 0.05)
                w_views   = st.slider("가중치: 조회수", 0.0, 1.0, 0.4, 0.05)
                w_likes   = st.slider("가중치: 좋아요", 0.0, 1.0, 0.2, 0.05)
                w_short   = st.slider("가중치: 쇼츠(<=60s)", 0.0, 1.0, 0.2, 0.05)
                st.caption("※ 결측 컬럼은 0으로 계산됩니다.")

        # 정렬/점수 적용 버튼
        apply_sort = st.button("정렬 적용 → 아래 공용 시트 업데이트", use_container_width=True)

        if apply_sort:
            view = base.copy()
            if use_rank:
                view = utils.add_composite_score(view,
                                                 w_recency=w_recency,
                                                 w_views=w_views,
                                                 w_likes=w_likes,
                                                 w_short=w_short)
            by_cols = [primary]
            asc_list = [primary_asc]
            if secondary != "(없음)":
                by_cols.append(secondary)
                asc_list.append(secondary_asc)
            # 점수가 있다면 최우선
            if "score" in view.columns and use_rank:
                by_cols = ["score"] + by_cols
                asc_list = [False] + asc_list

            view = view.sort_values(by=by_cols, ascending=asc_list)
            ss["yt_results_view"] = view
            st.success("정렬/랭킹 반영 완료! 아래 공용 시트를 확인하세요.")

# -----------------------------
# ▼ 페이지 하단: 공용 시트 (두 탭에서 공유)
# -----------------------------
with shared_table:
    st.divider()
    st.subheader("📊 공용 결과 시트")
    df_view = ss["yt_results_view"]

    if df_view.empty:
        st.info("아직 데이터가 없습니다. 탭에서 검색/정렬을 진행하세요.")
    else:
        # UI에는 숨길 컬럼 (내부 데이터는 그대로 유지)
        HIDE_COLS = ["videoId", "url"]

        # 2) 표시용 DF 생성
        df_display = df_view.drop(columns=HIDE_COLS, errors="ignore").copy()

        # 3) video_url 컬럼 생성 보장 (우선순위: 기존 video_url → url → videoId로 생성)
        if "video_url" not in df_display.columns:
            if "url" in df_view.columns:
                df_display["video_url"] = df_view["url"]
            elif "videoId" in df_view.columns:
                df_display["video_url"] = df_view["videoId"].apply(
                    lambda v: f"https://www.youtube.com/watch?v={v}" if pd.notna(v) else None
                )
            else:
                df_display["video_url"] = None

        # 4) 제목 컬럼 바로 뒤에 video_url 배치
        title_col = "video_title" if "video_title" in df_display.columns else ("title" if "title" in df_display.columns else None)
        if title_col and "video_url" in df_display.columns:
            cols = df_display.columns.tolist()
            # 먼저 위치에서 제거
            if "video_url" in cols:
                cols.remove("video_url")
            # 제목 바로 뒤 위치 계산
            insert_pos = cols.index(title_col) + 1 if title_col in cols else 1
            cols.insert(insert_pos, "video_url")
            df_display = df_display[cols]

        # 5) column_config: video_url을 아이콘 링크로, 썸네일은 이미지로
        colcfg = {}
        if "video_url" in df_display.columns:
            colcfg["video_url"] = st.column_config.LinkColumn(" ", display_text="▶️")  # 유튜브 아이콘 느낌의 플레이 버튼
        if "thumbnail" in df_display.columns:
            colcfg["thumbnail"] = st.column_config.ImageColumn("썸네일", width="small")

        # 6) 렌더
        st.dataframe(df_display, use_container_width=True, height=520, column_config=colcfg)

        # (선택) 화면에 보이는 열만 CSV로 저장 (숨김 열 제외)
        st.download_button(
            "CSV 다운로드(표시 열만)",
            data=df_display.to_csv(index=False).encode("utf-8"),
            file_name="youtube_results_view_display.csv",
            mime="text/csv"
        )
