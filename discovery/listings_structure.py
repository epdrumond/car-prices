"""
Generic, site-agnostic parsing of a single HTML page to support discovery (not production extraction).
"""
from __future__ import annotations

import json
import re
from collections import Counter
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

_RE_PRICE_BR = re.compile(
    r"R\$\s*[\d]{1,3}(?:\.\d{3})*,\d{2}|R\$\s*[\d]+[.,][\d]+|R\$\s*[\d]+",
    re.IGNORECASE,
)
_MAX_JSON_SCRIPT_CHARS = 18_000
_MAX_LINKS = 100
_MAX_DATA_ELS = 45
_MAX_SEMANTIC = 25
_TAG_FREQ_TOP = 40


def _json_preview(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        keys = list(obj.keys())
        return {
            "kind": "object",
            "n_keys": len(keys),
            "key_sample": keys[:30],
        }
    if isinstance(obj, list):
        out: dict = {"kind": "array", "len": len(obj)}
        if obj and isinstance(obj[0], dict):
            out["first_object_keys"] = list(obj[0].keys())[:25]
        return out
    if isinstance(obj, (str, int, float, bool)):
        return obj
    return str(type(obj).__name__)


def _safe_json_loads(s: str) -> Any | None:
    s = s.strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None


def _netloc(u: str) -> str:
    p = urlparse(u)
    return f"{p.scheme}://{p.netloc}" or ""


def extract_listings_page_structure(html: str, final_url: str) -> dict[str, Any]:
    """Parse one page; return a structured summary (no site-specific selectors)."""
    soup = BeautifulSoup(html, "html.parser")
    base = final_url
    page_netloc = urlparse(base).netloc

    t_el = soup.find("title")
    title = t_el.get_text(strip=True)[:800] if t_el else None
    meta_desc = None
    md = soup.find("meta", attrs={"name": "description"})
    if isinstance(md, Tag) and md.get("content"):
        meta_desc = md["content"].strip()[:2000]
    h1s = [h.get_text(strip=True)[:400] for h in soup.find_all("h1")[:12]]

    og: dict[str, str] = {}
    for p in ("og:title", "og:description", "og:url", "og:type"):
        m = soup.find("meta", attrs={"property": p})
        if isinstance(m, Tag) and m.get("content"):
            og[p] = m["content"].strip()[:500]

    all_tags = [e.name for e in soup.find_all() if e.name]
    tag_freq = Counter(all_tags).most_common(_TAG_FREQ_TOP)
    body = soup.find("body")
    text_blob = body.get_text(" ", strip=True) if body else soup.get_text(" ", strip=True)
    approx_len = len(text_blob)
    price_hits = len(_RE_PRICE_BR.findall(text_blob[:500_000]))

    embedded: list[dict[str, Any]] = []

    for s in soup.find_all("script", type=lambda x: x and "ld+json" in str(x).lower()):
        if not isinstance(s, Tag) or not s.string:
            continue
        raw = s.string.strip()[:_MAX_JSON_SCRIPT_CHARS]
        data = _safe_json_loads(raw)
        if data is not None:
            embedded.append(
                {
                    "type": "script_ld_json_like",
                    "json_preview": _json_preview(data),
                }
            )

    for s in soup.find_all("script", type=lambda x: x and "json" in str(x).lower() and "ld" not in str(x).lower()):
        if not isinstance(s, Tag) or not s.string:
            continue
        raw = s.string.strip()[:_MAX_JSON_SCRIPT_CHARS]
        if len(raw) < 2:
            continue
        data = _safe_json_loads(raw)
        if data is not None and not any(
            e.get("json_preview") == _json_preview(data) for e in embedded
        ):
            embedded.append(
                {
                    "type": "script_application_json",
                    "json_preview": _json_preview(data),
                }
            )

    nd = soup.find("script", id="__NEXT_DATA__")
    if isinstance(nd, Tag) and nd.string:
        raw = nd.string.strip()[:_MAX_JSON_SCRIPT_CHARS]
        data = _safe_json_loads(raw)
        if data is not None:
            embedded.append(
                {
                    "type": "script_id_next_data",
                    "json_preview": _json_preview(data),
                }
            )

    links_out: list[dict[str, str]] = []
    seen_href: set[str] = set()
    for a in soup.find_all("a", href=True):
        if not isinstance(a, Tag):
            continue
        href = str(a.get("href", "")).strip()
        if not href or href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        absu = urljoin(base, unescape(href))
        p = urlparse(absu)
        if p.netloc and p.netloc != page_netloc:
            continue
        if absu in seen_href and len(links_out) > 0:
            continue
        seen_href.add(absu)
        label = a.get_text(strip=True)[:200]
        links_out.append({"href": absu[:2000], "text": label})
        if len(links_out) >= _MAX_LINKS:
            break

    data_els: list[dict[str, Any]] = []
    for el in soup.find_all(True, limit=8000):
        if not isinstance(el, Tag):
            continue
        attrs = {
            k: (v if isinstance(v, str) and len(v) < 400 else "[long]")
            for k, v in el.attrs.items()
            if k.startswith("data-")
        }
        if not attrs:
            continue
        data_els.append(
            {
                "tag": el.name,
                "attrs": attrs,
            }
        )
        if len(data_els) >= _MAX_DATA_ELS:
            break

    semantic: list[dict[str, Any]] = []
    for el in soup.find_all(["main", "article", "section"], limit=120):
        if not isinstance(el, Tag):
            continue
        cl = el.get("class", [])
        cls = " ".join(cl[:3]) if isinstance(cl, list) else str(cl)[:120]
        did = (el.get("id") or "")[:120]
        dattrs = {k: v for k, v in el.attrs.items() if k.startswith("data-")}
        semantic.append(
            {
                "tag": el.name,
                "id": did or None,
                "class_sample": cls or None,
                "data_attr_keys": list(dattrs.keys())[:15],
            }
        )
        if len(semantic) >= _MAX_SEMANTIC:
            break

    return {
        "page": {
            "title": title,
            "meta_description": meta_desc,
            "h1": h1s,
            "open_graph": og,
            "origin_netloc": page_netloc,
        },
        "dom_summary": {
            "tag_frequency_top": [{"tag": a, "count": b} for a, b in tag_freq],
            "approx_visible_text_length": approx_len,
            "pattern_r_currency_substrings": price_hits,
        },
        "embedded_json_blocks": embedded,
        "internal_links_sample": links_out,
        "elements_with_data_attributes_sample": data_els,
        "semantic_containers_sample": semantic,
    }
