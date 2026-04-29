"""
Webmotors list page → structured rows for discovery.

1. **JSON-LD** ``script#jsonld_offercatalog_rb`` — title, price, images, URLs (Schema.org).
2. **URL path** on each *comprar* / listing link — model year or ``YYYY-YYYY`` range (segment before ad id).
3. **``__NEXT_DATA__``** — search query (e.g. ``estadocidade``) and filter hints (not per-listing).
4. **DOM vehicle cards** — when present, merge **km** and **location** from card markup. This includes
   **OEM** ``data-testid="vehicle_card_…"`` blocks, and **horizontal / mobile** used cards where the
   listing link is under ``/comprar/…/AD_ID``: we detect a parent ``div`` whose CSS-module class
   contains ``_Card_`` and read **location** from a ``div`` with ``_Location_`` in the class, plus
   a ``<p>`` whose text looks like odometer (e.g. ``30.567 Km``), ``/`` ``São Paulo (SP)`` for city/UF.
   Listing id comes from the **comprar** URL and matches JSON-LD on ``source_listing_id``.

   Some **HTTP** responses (bot/skeleton variants) return almost no card markup, only JSON-LD in
   a script. In that case odometer/location stay ``null`` and ``field_sources`` reflect the gap.
"""
from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup, Tag

_DOM_MILEAGE = "html.vehicle_card"  # merged from card DOM
_DOM_LOCATION = "html.vehicle_card"
_SSR_MILEAGE = "not_in_ssr"
_SSR_LOCATION = "not_in_ssr"
_ODOM_TESTID = re.compile(r"odometer|hodomet|quilom", re.I)
_LOCN_TESTID = re.compile(
    r"location|locali[sz]a|address|place|cidade|municip|\bcity\b|uf(?!$)|\bstate\b|seller|vendedor|dealer|loja",
    re.I,
)


def _listing_id_from_url(url: str) -> str | None:
    return listing_id_from_webmotors_href(url)


def listing_id_from_webmotors_href(href: str) -> str | None:
    """
    Ad id: last /segment of comprar/… URLs, or the numeric segment before ``quero-negociar`` /
    short paths like ``/marca/…/386043/quero-negociar``.
    """
    try:
        path = href.split("?", 1)[0].rstrip("/")
        segs = [s for s in path.split("/") if s]
    except (AttributeError, TypeError, ValueError):
        return None
    if not segs:
        return None
    for j in range(len(segs) - 1, -1, -1):
        s = segs[j]
        if s.isdigit() and len(s) >= 5:
            return s
    for j in range(len(segs) - 1, -1, -1):
        s = segs[j]
        if s.isdigit() and 4 <= len(s) <= 9:
            return s
    for j in range(len(segs) - 1, -1, -1):
        if segs[j].isdigit():
            return segs[j]
    return None


def parse_odometer_km_brazilian(text: str) -> int | None:
    """E.g. ``0 Km``, ``45.000 Km`` (BR thousands)."""
    if not (text and text.strip()):
        return None
    t = re.sub(r"\s*km\s*$", "", text.strip(), flags=re.IGNORECASE).strip()
    t = t.replace(" ", "")
    m = re.fullmatch(r"(\d{1,3}(?:\.\d{3})*|\d+)", t)
    if not m:
        return None
    raw = m.group(1)
    if "." in raw and re.match(r"^\d{1,3}(?:\.\d{3})+$", raw):
        return int(raw.replace(".", ""))
    return int(raw)


def parse_city_state_brazil(s: str) -> tuple[str | None, str | None, str | None]:
    """``Curitiba - PR``, ``São Paulo / SP``, or ``São Paulo (SP)`` — (city, state_uf, full)."""
    t = (s or "").strip()
    if not t:
        return None, None, None
    m0 = re.match(
        r"^(.+?)\s+\(([A-Za-z]{2})\)\s*$",
        t,
    )
    if m0:
        city = m0.group(1).strip()
        uf = m0.group(2).upper()
        return city, uf, t
    m = re.match(
        r"^(.+?)\s*[-/–—]\s*([A-Za-z]{2})\s*$",
        t,
    )
    if m:
        city = m.group(1).strip()
        uf = m.group(2).upper()
        return city, uf, t
    return None, None, t


def _get_testid_text(container: Tag, rxc: re.Pattern[str]) -> str:
    for el in container.find_all(True, attrs={"data-testid": True}):
        if el.name in ("script", "style"):
            continue
        tid = (el.get("data-testid") or "").strip()
        if rxc.search(tid):
            txt = el.get_text(" ", strip=True)
            if txt:
                return txt
    return ""


def _is_vehicle_card_container(tid: str) -> bool:
    t = (tid or "").lower()
    if "skeleton" in t:
        return False
    if "container" in t and "vehicle_card" in t:
        return True
    return re.search(r"vehicle_card\w*container$", t, re.I) is not None


def _classes_str(tag: Tag) -> str:
    cl = tag.get("class")
    if not cl:
        return ""
    return " ".join(cl) if isinstance(cl, list) else str(cl)


def _find_comprar_card_root(anchor: Tag) -> Tag | None:
    """Narrowest ancestor ``div`` whose class looks like a CSS-module card (e.g. ``_Card_…``)."""
    for p in anchor.parents:
        if not isinstance(p, Tag) or p.name != "div":
            continue
        s = _classes_str(p)
        if re.search(r"_[Cc]ard_[A-Za-z0-9_]+", s):
            return p
    return None


def _odometer_text_comprar_card(card: Tag) -> str:
    for p in card.find_all("p"):
        t = p.get_text(" ", strip=True)
        if not re.search(r"[\d.]+", t) or not re.search(r"(?i)km\s*$", t):
            continue
        if re.fullmatch(r"\d{4}(/\d{4})?", t.replace(" ", "")):
            continue
        return t
    return ""


def _location_text_comprar_card(card: Tag) -> str:
    for d in card.find_all("div"):
        if "_Location_" in _classes_str(d):
            p = d.find("p")
            if p:
                t = p.get_text(" ", strip=True)
                if t:
                    return t
    return ""


def _row_from_comprar_card(card: Tag) -> dict[str, Any] | None:
    odo_txt = _odometer_text_comprar_card(card)
    loc_txt = _location_text_comprar_card(card)
    km = parse_odometer_km_brazilian(odo_txt) if odo_txt else None
    city, state, loc_line = (None, None, None)
    if loc_txt:
        city, state, loc_line = parse_city_state_brazil(loc_txt)
    if km is None and not loc_txt and not odo_txt:
        return None
    return {
        "mileage_km": km,
        "odometer_text": odo_txt or None,
        "listing_location_text": loc_line,
        "listing_city": city,
        "listing_state": state,
    }


def _index_comprar_horizontal_card_rows(soup: BeautifulSoup) -> dict[str, dict[str, Any]]:
    """
    Mobile / horizontal used results: no ``vehicle_card`` testids; ``_Card_`` + ``_Location_`` in classes.
    """
    out: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        h = str(a.get("href") or "").strip()
        if "/comprar/" not in h.lower():
            continue
        h_abs = "https://www.webmotors.com.br" + h if h.startswith("/") else h
        if "webmotors" not in h_abs and not h.startswith("/"):
            continue
        sid = listing_id_from_webmotors_href(h_abs)
        if not sid or sid in seen:
            continue
        card = _find_comprar_card_root(a)
        if not card:
            continue
        row = _row_from_comprar_card(card)
        if not row:
            continue
        seen.add(sid)
        out[sid] = row
    return out


def _merge_listing_card_dom_entry(
    out: dict[str, dict[str, Any]], sid: str, b: dict[str, Any]
) -> None:
    if sid not in out:
        out[sid] = b
        return
    a = out[sid]
    if a.get("mileage_km") is None and b.get("mileage_km") is not None:
        a["mileage_km"] = b["mileage_km"]
    if not a.get("odometer_text") and b.get("odometer_text"):
        a["odometer_text"] = b["odometer_text"]
    for k in ("listing_location_text", "listing_city", "listing_state"):
        if a.get(k) in (None, "") and b.get(k) is not None:
            a[k] = b[k]


def extract_vehicle_card_dom_index(soup: BeautifulSoup) -> dict[str, dict[str, Any]]:
    """
    Index ``source_listing_id`` → odometer / location from ``data-testid="…vehicle_card*…_container"``
    (e.g. OEM 0 km cards) and similar blocks.
    """
    out: dict[str, dict[str, Any]] = {}
    for container in soup.find_all(True, attrs={"data-testid": True}):
        if not isinstance(container, Tag) or not _is_vehicle_card_container(
            (container.get("data-testid") or "").strip()
        ):
            continue
        sid: str | None = None
        best: tuple[int, str] | None = None
        for a in container.find_all("a", href=True):
            h = str(a.get("href") or "").strip()
            if "webmotors" not in h and not h.startswith("/"):
                continue
            h_abs = "https://www.webmotors.com.br" + h if h.startswith("/") else h
            lid = listing_id_from_webmotors_href(h_abs)
            if not lid:
                continue
            priority = 2 if "/comprar/" in h else 1
            if best is None or priority > best[0] or (priority == best[0] and h > best[1]):
                best = (priority, h)
                sid = lid
        if not sid:
            continue
        odo_txt = _get_testid_text(container, _ODOM_TESTID)
        if not odo_txt:
            for p in container.find_all("p", attrs={"data-testid": True}):
                pt = (p.get("data-testid") or "")
                if "odometer" in pt.lower() or "hodomet" in pt.lower() or "quilom" in pt.lower():
                    odo_txt = p.get_text(" ", strip=True) or odo_txt
        loc_txt = _get_testid_text(container, _LOCN_TESTID)
        km = parse_odometer_km_brazilian(odo_txt) if odo_txt else None
        city, state, loc_line = (None, None, None)
        if loc_txt:
            city, state, loc_line = parse_city_state_brazil(loc_txt)
        out[sid] = {
            "mileage_km": km,
            "odometer_text": odo_txt or None,
            "listing_location_text": loc_line,
            "listing_city": city,
            "listing_state": state,
        }
    for sid, row in _index_comprar_horizontal_card_rows(soup).items():
        _merge_listing_card_dom_entry(out, sid, row)
    return out


def parse_model_years_from_comprar_url(url: str) -> dict[str, Any]:
    """
    Webmotors *comprar* paths include a year segment before the numeric ad id, e.g.:
    ``.../4-portas/2018-2019/67004287`` or ``.../4-portas/2023/67459392``.
    """
    try:
        path = url.split("?", 1)[0].rstrip("/")
        segs = [s for s in path.split("/") if s]
        if not segs or not segs[-1].isdigit():
            return {}
        yseg = segs[-2] if len(segs) >= 2 else ""
        m = re.fullmatch(r"(\d{4})-(\d{4})", yseg)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            return {
                "model_year_label": yseg,
                "model_year_start": a,
                "model_year_end": b,
            }
        m2 = re.fullmatch(r"(\d{4})", yseg)
        if m2:
            y = int(m2.group(1))
            return {
                "model_year_label": yseg,
                "model_year_start": y,
                "model_year_end": y,
            }
    except (ValueError, IndexError, AttributeError):
        pass
    return {}


def extract_search_context_from_html(html: str) -> dict[str, Any]:
    """``__NEXT_DATA__`` page query + list-level location filter (not each card)."""
    soup = BeautifulSoup(html, "html.parser")
    el = soup.find("script", id="__NEXT_DATA__")
    if not el or not el.string:
        return {}
    try:
        d = json.loads(el.string.strip())
    except json.JSONDecodeError:
        return {}
    q: dict = d.get("query") or {}
    pp: dict = (d.get("props") or {}).get("pageProps") or {}
    floc: dict = ((pp.get("filters") or {}).get("location") or {}) if isinstance(pp.get("filters"), dict) else {}
    return {
        "next_query": q,
        "search_estadocidade": q.get("estadocidade"),
        "search_tipoveiculo": q.get("tipoveiculo"),
        "search_page": q.get("page"),
        "filter_location_state": floc.get("state"),
        "filter_location_city": floc.get("city"),
        "filter_location_filled": floc.get("filled"),
    }


def extract_webmotors_listings_from_html(html: str) -> list[dict[str, Any]]:
    """
    Same rows as in :func:`extract_webmotors_page_bundle` (JSON-LD plus vehicle-card DOM
    when present), without the top-level search context / dom stats.
    """
    return extract_webmotors_page_bundle(html)["listings"]


def extract_webmotors_page_bundle(html: str) -> dict[str, Any]:
    """
    Full discovery bundle: search context, enriched listings, and SSR limitations note.
    """
    soup = BeautifulSoup(html, "html.parser")
    el = soup.find("script", id="jsonld_offercatalog_rb")
    if not el or not el.string:
        return {
            "search_context": extract_search_context_from_html(html),
            "listings": [],
            "ssr_data_note": (
                "No jsonld_offercatalog_rb or invalid JSON. If HTML was truncated, increase "
                "SCRAPE_MAX_BYTES_SAVED and refetch."
            ),
        }

    try:
        data = json.loads(el.string.strip())
    except json.JSONDecodeError:
        return {
            "search_context": extract_search_context_from_html(html),
            "listings": [],
            "ssr_data_note": "JSON-LD block failed to parse (truncated mid-script?).",
        }
    if data.get("@type") != "OfferCatalog":
        return {
            "search_context": extract_search_context_from_html(html),
            "listings": [],
            "ssr_data_note": "Expected OfferCatalog in jsonld_offercatalog_rb.",
        }

    search_context = extract_search_context_from_html(html)
    out: list[dict[str, Any]] = []
    for li in data.get("itemListElement") or []:
        if not isinstance(li, dict) or li.get("@type") != "ListItem":
            continue
        it = li.get("item")
        if not isinstance(it, dict) or it.get("@type") != "Vehicle":
            continue
        off = it.get("offers")
        off = off if isinstance(off, dict) else {}
        url = (off.get("url") or "").strip()
        sid = _listing_id_from_url(url) if url else None
        imgs = it.get("image")
        if isinstance(imgs, str):
            img_list: list[str] = [imgs]
        elif isinstance(imgs, list):
            img_list = [str(x) for x in imgs if x]
        else:
            img_list = []
        years = parse_model_years_from_comprar_url(url) if url else {}
        row: dict[str, Any] = {
            "title": it.get("name"),
            "price_brl": off.get("price"),
            "price_currency": off.get("priceCurrency"),
            "listing_url": url,
            "source_listing_id": sid,
            "image_urls": img_list,
            "availability": off.get("availability"),
            "mileage_km": None,
            "listing_city": None,
            "listing_state": None,
            "listing_location_text": None,
            "field_sources": {
                "title": "json_ld.vehicle",
                "price_brl": "json_ld.offer",
                "model_year": "listing_url_path" if years else "unparsed",
                "mileage_km": _SSR_MILEAGE,
                "listing_location": _SSR_LOCATION,
            },
        }
        row.update(years)
        out.append(row)

    dom = extract_vehicle_card_dom_index(soup)
    nm = nl = 0
    for row in out:
        sid = row.get("source_listing_id")
        if not isinstance(sid, str) or sid not in dom:
            continue
        d = dom[sid]
        if d.get("mileage_km") is not None:
            row["mileage_km"] = d["mileage_km"]
            row["field_sources"]["mileage_km"] = _DOM_MILEAGE
            nm += 1
        if d.get("listing_location_text") is not None or d.get("listing_city") is not None or d.get("listing_state") is not None:
            for k in ("listing_location_text", "listing_city", "listing_state"):
                v = d.get(k)
                if v is not None:
                    row[k] = v
            row["field_sources"]["listing_location"] = _DOM_LOCATION
            nl += 1

    ssr_note = (
        "Listings are built from JSON-LD, with model year from the *comprar* URL path. "
        "Odometer (km) and per-listing location are read from **vehicle card** markup when present: "
        "OEM blocks use `data-testid` (e.g. `vehicle_card_oem_container`, `…_odometer`); "
        "used / horizontal cards use a parent `div` with `_Card_` in the class, odometer in a `<p>` "
        "ending in `Km`, and location in a `div` with `_Location_` in the class (e.g. `São Paulo (SP)`), "
        "all merged by `source_listing_id`. Some HTTP responses are mostly skeletons; then "
        "mileage/location can stay null. Search-level geography is in `search_context`, not seller city."
    )
    return {
        "search_context": search_context,
        "listings": out,
        "count": len(out),
        "vehicle_card_dom": {
            "cards_indexed": len(dom),
            "rows_merged_mileage": nm,
            "rows_merged_location": nl,
        },
        "ssr_data_note": ssr_note,
    }
