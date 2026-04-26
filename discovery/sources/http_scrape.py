"""
Conservative, single-page HTTP fetch for discovery (not API-based).

- By default: **1 GET** per run, **5 s** delay before the request, **~150 KB** max saved body.
- Target URL from **SCRAPE_URL** (never commit real URLs; use env or `config/local/`).
- No link following, no parallel requests, no retries (one attempt only).
"""
from __future__ import annotations

import os
import time
from email.utils import formatdate
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from discovery.paths import OUTPUT_DIR
from discovery.writers import write_json

OUTPUT_META = OUTPUT_DIR / "http_scrape_sample.json"
OUTPUT_BODY = OUTPUT_DIR / "http_scrape_body.html"

# Defaults are intentionally strict; override only via env for local experiments.
def _i(name: str, default: int) -> int:
    v = os.environ.get(name, "").strip()
    return int(v) if v else default


def _f(name: str, default: float) -> float:
    v = os.environ.get(name, "").strip()
    return float(v) if v else default


MAX_REQUESTS = _i("SCRAPE_MAX_REQUESTS", 1)  # must stay 1 for this module
MIN_DELAY_S = _f("SCRAPE_MIN_DELAY_S", 5.0)
MAX_BYTES = _i("SCRAPE_MAX_BYTES_SAVED", 150_000)
TIMEOUT_S = _i("SCRAPE_TIMEOUT", 20)
USER_AGENT = os.environ.get(
    "SCRAPE_USER_AGENT",
    "car-prices-discovery/0.1 (research; conservative single-GET; contact: project owner)",
)


def _url_ok(url: str) -> bool | str:
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        return "only http(s) allowed"
    if not p.netloc:
        return "missing host"
    host = (p.hostname or "").lower()
    if host in ("localhost", "127.0.0.1", "::1"):
        return "local hosts blocked"
    return True


def collect_http_scrape_sample() -> str:
    url = (os.environ.get("SCRAPE_URL") or "").strip()
    if not url:
        write_json(
            OUTPUT_META,
            {
                "status": "skipped",
                "message": "Set SCRAPE_URL to one public page. No request was made.",
                "constraints": {
                    "max_requests": MAX_REQUESTS,
                    "min_delay_s_before_request": MIN_DELAY_S,
                    "max_bytes_saved": MAX_BYTES,
                    "timeout_s": TIMEOUT_S,
                },
            },
        )
        return str(OUTPUT_META)

    if MAX_REQUESTS != 1:
        write_json(
            OUTPUT_META,
            {
                "status": "error",
                "message": "This module only supports SCRAPE_MAX_REQUESTS=1 for now.",
                "scrape_max_requests": MAX_REQUESTS,
            },
        )
        return str(OUTPUT_META)

    bad = _url_ok(url)
    if bad is not True:
        write_json(
            OUTPUT_META,
            {"status": "error", "message": f"URL not allowed: {bad}", "url": url},
        )
        return str(OUTPUT_META)

    time.sleep(MIN_DELAY_S)

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.5",
    }
    try:
        r = requests.get(
            url,
            headers=headers,
            timeout=TIMEOUT_S,
            allow_redirects=True,
        )
    except requests.RequestException as e:
        write_json(
            OUTPUT_META,
            {
                "status": "error",
                "url": url,
                "message": str(e),
                "requests_made": 0,
            },
        )
        return str(OUTPUT_META)

    body = r.content
    if len(body) > MAX_BYTES:
        body = body[:MAX_BYTES]
        truncated = True
    else:
        truncated = False

    text = body.decode("utf-8", errors="replace")
    OUTPUT_BODY.write_text(text, encoding="utf-8")

    title = None
    meta_desc = None
    h1 = []
    if "html" in (r.headers.get("Content-Type") or "").lower() or text.lstrip().lower().startswith("<!doctype html") or "<html" in text[:2000].lower():
        soup = BeautifulSoup(text, "html.parser")
        t = soup.find("title")
        if t and t.string:
            title = t.string.strip()[:500]
        md = soup.find("meta", attrs={"name": "description"})
        if md and md.get("content"):
            meta_desc = md["content"].strip()[:1000]
        h1 = [h.get_text(strip=True)[:200] for h in soup.find_all("h1")[:5]]

    out = {
        "status": "ok",
        "url": url,
        "fetched_at_http_date": formatdate(usegmt=True),
        "http_status": r.status_code,
        "final_url": r.url,
        "content_type": r.headers.get("Content-Type"),
        "bytes_saved": len(body),
        "body_truncated": truncated,
        "body_path": str(OUTPUT_BODY.name),
        "requests_made": 1,
        "constraints": {
            "max_requests": MAX_REQUESTS,
            "min_delay_s_before_request": MIN_DELAY_S,
            "max_bytes_saved": MAX_BYTES,
            "timeout_s": TIMEOUT_S,
        },
        "parsed_preview": {
            "title": title,
            "meta_description": meta_desc,
            "h1_up_to_5": h1,
        },
    }
    write_json(OUTPUT_META, out)
    return str(OUTPUT_META)
