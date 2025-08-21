import re
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

ISO8601_DURATION_RE = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")

def parse_duration_iso8601(s: str) -> int:
    if not isinstance(s, str):
        return 0
    m = ISO8601_DURATION_RE.fullmatch(s)
    if not m:
        return 0
    h, mnt, sec = m.groups()
    h = int(h) if h else 0
    mnt = int(mnt) if mnt else 0
    sec = int(sec) if sec else 0
    return h*3600 + mnt*60 + sec


def df_from_youtube_items(items: list) -> pd.DataFrame:
    """
    YouTube Data API v3 search/list 응답의 items -> DataFrame (유연 플래튼)
    지원 키:
    - id.videoId / id
    - snippet.title, snippet.channelTitle, snippet.publishedAt, snippet.thumbnails.medium.url
    - contentDetails.duration
    - statistics.viewCount, statistics.likeCount
    """
    rows = []
    for it in items:
        # id / videoId
        vid = None
        if isinstance(it.get("id"), dict):
            vid = it["id"].get("videoId") or it["id"].get("video_id")
        else:
            vid = it.get("videoId") or it.get("id")
        sn = it.get("snippet", {})
        cd = it.get("contentDetails", {})
        stt = it.get("statistics", {})

        row = {
            "videoId": vid,
            "title": sn.get("title"),
            "channelTitle": sn.get("channelTitle"),
            "publishedAt": sn.get("publishedAt"),
            "thumbnail": (((sn.get("thumbnails") or {}).get("medium") or {}).get("url"))
                         or (((sn.get("thumbnails") or {}).get("default") or {}).get("url")),
            "durationIso": cd.get("duration"),
            "viewCount": stt.get("viewCount"),
            "likeCount": stt.get("likeCount"),
        }
        # 숫자 캐스팅
        for k in ["viewCount", "likeCount"]:
            if row[k] is not None:
                try:
                    row[k] = int(row[k])
                except Exception:
                    row[k] = None
        # duration
        row["durationSec"] = parse_duration_iso8601(row["durationIso"]) if row["durationIso"] else None
        rows.append(row)

    df = pd.DataFrame(rows)
    return df

def aspect_score(w, h, prefer_vertical=True):
    if not w or not h:
        return 0
    r = w / h
    target = 9/16 if prefer_vertical else 16/9
    return 1 - min(1, abs(r - target) / target)

def compute_score(item, prefer_vertical=True):
    provider_weight = 1.0 if item["provider"] in ["wikimedia","openverse","pexels","pixabay"] else 0.7
    return 0.6*aspect_score(item.get("width"), item.get("height"), prefer_vertical) + 0.4*provider_weight

def dedup_items(items):
    seen, out = set(), []
    for it in items:
        k = (it["provider"], it.get("source_url") or it.get("download") or it.get("preview"))
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out

def license_block(item):
    return f"**License**: {item.get('license','?')}  \n**Attribution**: {item.get('attribution','')}  \n**Source**: {item.get('source_url','')}"

def csv_from_items(items):
    headers = ["provider","type","preview","download","width","height","duration","license","attribution","source_url"]
    lines = [",".join(headers)]
    for it in items:
        row = []
        for k in headers:
            v = str(it.get(k,"")).replace(",", " ")
            row.append(v)
        lines.append(",".join(row))
    return "\n".join(lines).encode("utf-8")


def parse_duration_iso8601(s: str) -> int:
    if not isinstance(s, str):
        return 0
    m = ISO8601_DURATION_RE.fullmatch(s)
    if not m:
        return 0
    h, mnt, sec = m.groups()
    h = int(h) if h else 0
    mnt = int(mnt) if mnt else 0
    sec = int(sec) if sec else 0
    return h*3600 + mnt*60 + sec

def df_from_service(data) -> pd.DataFrame:
    """
    Cloud Run 응답을 유연하게 DataFrame으로 변환.
    지원:
      - {"columns":[...], "values":[[...], ...]}
      - {"items":[...]}, {"results":[...]}, {"data":[...]} 또는 리스트 자체
    """
    if isinstance(data, dict) and "columns" in data and "values" in data:
        return pd.DataFrame(data["values"], columns=data["columns"])

    items = None
    if isinstance(data, dict):
        items = data.get("items") or data.get("results") or data.get("data")
    else:
        items = data

    if isinstance(items, list):
        # dict 리스트면 normalize, 스칼라 리스트면 그대로 컬럼 하나
        if items and isinstance(items[0], dict):
            return pd.json_normalize(items)
        return pd.DataFrame({"value": items})
    elif isinstance(items, dict):
        return pd.json_normalize(items)
    else:
        return pd.DataFrame()

def normalize_youtube_df(df: pd.DataFrame) -> pd.DataFrame:
    # duration
    if "durationIso" in df.columns and "durationSec" not in df.columns:
        df["durationSec"] = df["durationIso"].apply(parse_duration_iso8601)
    if "duration_sec" in df.columns and "durationSec" not in df.columns:
        df["durationSec"] = pd.to_numeric(df["duration_sec"], errors="coerce")

    if "durationSec" in df.columns:
        df["isShorts"] = df["durationSec"].apply(lambda x: bool(x is not None and x <= 60))

    for k in ["viewCount","likeCount","durationSec","views_per_hour","likes_per_view","score"]:
        if k in df.columns:
            df[k] = pd.to_numeric(df[k], errors="coerce")
    return df

def ensure_url_columns(df: pd.DataFrame) -> pd.DataFrame:
    if "videoId" in df.columns and "url" not in df.columns:
        df["url"] = df["videoId"].apply(lambda v: f"https://www.youtube.com/watch?v={v}" if pd.notna(v) else None)
    return df

def standardize_cols(df: pd.DataFrame) -> pd.DataFrame:
    """snake_case/variant 컬럼명을 통일"""
    ren = {}
    cols = df.columns.str.strip().tolist()
    low = {c.lower(): c for c in cols}

    def has(name): return name in low

    # video id
    if has("video_id"): ren[low["video_id"]] = "videoId"
    # title & channel
    if has("channel_title"): ren[low["channel_title"]] = "channelTitle"
    # published
    if has("published_at"): ren[low["published_at"]] = "publishedAt"
    # counts
    if has("view_count"): ren[low["view_count"]] = "viewCount"
    if has("like_count"): ren[low["like_count"]] = "likeCount"
    # duration
    if has("durationsec"): ren[low["durationsec"]] = "durationSec"
    if has("duration_sec"): ren[low["duration_sec"]] = "durationSec"

    return df.rename(columns=ren)

def add_composite_score(df: pd.DataFrame, w_recency=0.4, w_views=0.4, w_likes=0.2, w_short=0.2) -> pd.DataFrame:
    df = df.copy()

    # ✅ 최신성: publishedAt 문자열을 바로 파싱(임시 시리즈, 컬럼 추가 안 함)
    if "publishedAt" in df.columns:
        dt_utc = pd.to_datetime(df["publishedAt"], utc=True, errors="coerce")
        now_utc = pd.Timestamp.utcnow().tz_localize("UTC")
        days = (now_utc - dt_utc).dt.total_seconds() / 86400
        recency = 1.0 / (1.0 + (days.clip(lower=0) / 7.0))  # 0~1
        recency = recency.fillna(0.0)
    else:
        recency = pd.Series(0.0, index=df.index)

    # 조회수/좋아요 로그 스케일
    if "viewCount" in df.columns:
        vc = df["viewCount"].fillna(0).clip(lower=0)
        views = vc.apply(lambda x: 0 if x <= 0 else min(1.0, (np.log10(x+1) / 7)))
    else:
        views = pd.Series(0.0, index=df.index)

    if "likeCount" in df.columns:
        lc = df["likeCount"].fillna(0).clip(lower=0)
        likes = lc.apply(lambda x: 0 if x <= 0 else min(1.0, (np.log10(x+1) / 6)))
    else:
        likes = pd.Series(0.0, index=df.index)

    if "isShorts" in df.columns:
        shorts = df["isShorts"].apply(lambda b: 1.0 if bool(b) else 0.0)
    else:
        shorts = pd.Series(0.0, index=df.index)

    df["score"] = (w_recency*recency + w_views*views + w_likes*likes + w_short*shorts).fillna(0.0)
    return df
