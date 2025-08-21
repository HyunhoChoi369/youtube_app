# lib/providers.py
import requests

def _safe_get(url, **kwargs):
    try:
        r = requests.get(url, timeout=20, **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}

def search_pexels(api_key: str, q: str, per_page=20, want_video=True, orientation=None):
    if not api_key: return []
    headers = {"Authorization": api_key}
    out = []

    # photos
    params = {"query": q, "per_page": per_page}
    if orientation: params["orientation"] = orientation
    j = _safe_get("https://api.pexels.com/v1/search", headers=headers, params=params)
    for p in j.get("photos", []):
        out.append({
            "provider":"pexels","type":"photo",
            "preview": p["src"]["medium"], "download": p["src"]["original"],
            "width": p.get("width"), "height": p.get("height"),
            "duration": None,
            "license": "Pexels License",
            "attribution": f'{p.get("photographer","")} (Pexels)',
            "source_url": p.get("url")
        })

    # videos
    if want_video:
        vj = _safe_get("https://api.pexels.com/videos/search",
                       headers=headers, params={"query": q, "per_page": per_page})
        for v in vj.get("videos", []):
            files = v.get("video_files", [])
            best = max(files, key=lambda f: f.get("width",0)*f.get("height",0)) if files else {}
            out.append({
                "provider":"pexels","type":"video",
                "preview": v.get("image"), "download": best.get("link"),
                "width": best.get("width"), "height": best.get("height"),
                "duration": v.get("duration"),
                "license": "Pexels License",
                "attribution": f'Pexels Video by {v.get("user",{}).get("name","")}',
                "source_url": v.get("url")
            })
    return out

def search_pixabay(api_key: str, q: str, per_page=20, want_video=True, safesearch=True):
    if not api_key: return []
    base_params = {"key": api_key, "q": q, "per_page": per_page, "safesearch": str(safesearch).lower()}
    out = []

    # photos
    j = _safe_get("https://pixabay.com/api/", params=base_params)
    for h in j.get("hits", []):
        out.append({
            "provider":"pixabay","type":"photo",
            "preview": h.get("previewURL"), "download": h.get("largeImageURL"),
            "width": h.get("imageWidth"), "height": h.get("imageHeight"),
            "duration": None,
            "license": "Pixabay Content License",
            "attribution": f'{h.get("user","")} (Pixabay)',
            "source_url": h.get("pageURL")
        })

    # videos
    if want_video:
        vj = _safe_get("https://pixabay.com/api/videos/", params=base_params)
        for h in vj.get("hits", []):
            vids = h.get("videos", {})
            best = vids.get("large") or vids.get("medium") or vids.get("small") or {}
            out.append({
                "provider":"pixabay","type":"video",
                "preview": h.get("picture_id") and f"https://i.vimeocdn.com/video/{h['picture_id']}_640x360.jpg",
                "download": best.get("url"),
                "width": best.get("width"), "height": best.get("height"),
                "duration": h.get("duration"),
                "license": "Pixabay Content License",
                "attribution": f'{h.get("user","")} (Pixabay)',
                "source_url": h.get("pageURL")
            })
    return out

def search_openverse(q: str, per_page=20, license_type="any"):
    params = {"q": q, "page_size": per_page}
    if license_type != "any":
        params["license_type"] = license_type
    j = _safe_get("https://api.openverse.org/v1/images/", params=params)
    out = []
    for r in j.get("results", []):
        out.append({
            "provider":"openverse","type":"photo",
            "preview": r.get("thumbnail"), "download": r.get("url"),
            "width": r.get("width"), "height": r.get("height"),
            "duration": None,
            "license": r.get("license","").upper(),
            "attribution": r.get("attribution","Openverse"),
            "source_url": r.get("foreign_landing_url") or r.get("url")
        })
    return out

def wikidata_p18_image(name: str):
    # 1) entity search
    s = _safe_get("https://www.wikidata.org/w/api.php",
                  params={"action":"wbsearchentities","search":name,"language":"ko","format":"json","limit":1})
    if not s.get("search"):
        return None
    qid = s["search"][0]["id"]

    # 2) entity detail
    e = _safe_get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")
    ent = e.get("entities", {}).get(qid, {})
    claims = ent.get("claims", {})
    if "P18" not in claims:
        return None
    filename = claims["P18"][0]["mainsnak"]["datavalue"]["value"]
    title = f"File:{filename}"

    # 3) commons meta
    c = _safe_get("https://commons.wikimedia.org/w/api.php",
                  params={"action":"query","prop":"imageinfo","iiprop":"url|extmetadata","titles":title,"format":"json"})
    pages = c.get("query", {}).get("pages", {})
    if not pages:
        return None
    page = next(iter(pages.values()))
    ii = (page.get("imageinfo") or [{}])[0]
    meta = ii.get("extmetadata", {})
    return {
        "provider":"wikimedia","type":"photo",
        "preview": ii.get("url"), "download": ii.get("url"),
        "width": None, "height": None, "duration": None,
        "license": meta.get("LicenseShortName", {}).get("value", ""),
        "attribution": (meta.get("Artist", {}).get("value", "") or "Wikimedia Commons").strip(),
        "source_url": f"https://commons.wikimedia.org/wiki/{title}"
    }

def search_youtube_cc(api_key: str, q: str, per_page=20):
    if not api_key: return []
    params = {
        "part":"snippet","q":q,"type":"video","maxResults":min(per_page,50),
        "videoLicense":"creativeCommon","safeSearch":"moderate"
    }
    j = _safe_get("https://www.googleapis.com/youtube/v3/search", params={**params, "key": api_key})
    out = []
    for item in j.get("items", []):
        vid = item["id"]["videoId"]
        thumb = item["snippet"]["thumbnails"]["medium"]["url"]
        out.append({
            "provider":"youtube","type":"video",
            "preview": thumb, "download": None,  # TOS상 다운로드 불가
            "width": None, "height": None, "duration": None,
            "license": "CC-BY (YouTube setting)",
            "attribution": item["snippet"].get("channelTitle","YouTube"),
            "source_url": f"https://www.youtube.com/watch?v={vid}"
        })
    return out
