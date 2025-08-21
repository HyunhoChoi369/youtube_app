# lib/utils.py
import streamlit as st

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
