"""
Generic one-page fetch + structure extraction for any listings URL (config/env).

- **1 GET** per run, conservative delay and size caps (same as former http_scrape).
- URL: `LISTINGS_PAGE_URL` env, or `listings_page_url` in `config/local/listings_page.yaml`,
  or `SCRAPE_URL` (legacy).
- Optional `source_label` in that YAML to suffix output files so runs do not overwrite.
"""
from __future__ import annotations

import os
import re
import time
from email.utils import formatdate
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml

from discovery.listings_structure import extract_listings_page_structure
from discovery.paths import DISCOVERY_DIR, OUTPUT_DIR, write_json

LOCAL_CONFIG = DISCOVERY_DIR.parent / "config" / "local" / "listings_page.yaml"

# Defaults: strict. Override with env for local tests.
def _i(name: str, default: int) -> int:
    v = os.environ.get(name, "").strip()
    return int(v) if v else default


def _f(name: str, default: float) -> float:
    v = os.environ.get(name, "").strip()
    return float(v) if v else default


MAX_REQUESTS = _i("SCRAPE_MAX_REQUESTS", 1)
MIN_DELAY_S = _f("SCRAPE_MIN_DELAY_S", 5.0)
MAX_BYTES = _i("SCRAPE_MAX_BYTES_SAVED", 1_000_000)
TIMEOUT_S = _i("SCRAPE_TIMEOUT", 20)
USER_AGENT = os.environ.get(
    "SCRAPE_USER_AGENT",
    "car-prices-discovery/0.1 (research; listings discovery; +contact owner)",
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


def _load_config() -> dict:
    p = os.environ.get("LISTINGS_PAGE_CONFIG", "").strip()
    path = Path(p) if p else LOCAL_CONFIG
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _label_from_cfg(cfg: dict) -> str | None:
    lab = cfg.get("source_label") or cfg.get("label")
    if not lab:
        return None
    s = re.sub(r"[^a-zA-Z0-9._-]+", "", str(lab))[:64]
    return s or None


def _resolve_url() -> tuple[str, str | None, str | None]:
    """
    Returns (url, source_label, config_path_used_display).
    """
    u = (os.environ.get("LISTINGS_PAGE_URL") or os.environ.get("SCRAPE_URL") or "").strip()
    conf_display = str(LOCAL_CONFIG) if LOCAL_CONFIG.is_file() else None
    p = os.environ.get("LISTINGS_PAGE_CONFIG", "").strip()
    if p:
        conf_display = p
    cfg = _load_config()
    label: str | None = None
    if isinstance(cfg, dict):
        if not u:
            raw = cfg.get("listings_page_url") or cfg.get("url")
            u = (str(raw).strip() if raw else "")
        label = _label_from_cfg(cfg)
    return u, label, conf_display


def _output_prefix(label: str | None) -> str:
    if label:
        return f"listings_page_{label}"
    return "listings_page"


def run_listings_discovery(
    *,
    url: str,
    source_label: str | None,
    file_prefix: str,
    mode: str,
    config_path_display: str | None,
) -> str:
    """
    Shared one-GET + extract. ``file_prefix`` names ``{file_prefix}_sample.json`` and ``_body.html``.
    """
    meta_path = OUTPUT_DIR / f"{file_prefix}_sample.json"
    body_path = OUTPUT_DIR / f"{file_prefix}_body.html"

    if MAX_REQUESTS != 1:
        write_json(
            meta_path,
            {"status": "error", "message": "Only SCRAPE_MAX_REQUESTS=1 is supported."},
        )
        return str(meta_path)

    bad = _url_ok(url)
    if bad is not True:
        write_json(
            meta_path,
            {"status": "error", "message": f"URL not allowed: {bad}", "url": url},
        )
        return str(meta_path)

    time.sleep(MIN_DELAY_S)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.5",
    }
    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT_S, allow_redirects=True)
    except requests.RequestException as e:
        write_json(
            meta_path,
            {
                "status": "error",
                "url": url,
                "message": str(e),
                "requests_made": 0,
            },
        )
        return str(meta_path)

    body = r.content
    truncated = len(body) > MAX_BYTES
    if truncated:
        body = body[:MAX_BYTES]
    text = body.decode("utf-8", errors="replace")
    body_path.write_text(text, encoding="utf-8")

    structure: object = {}
    if "html" in (r.headers.get("Content-Type") or "").lower() or "<html" in text[:5000].lower():
        try:
            structure = extract_listings_page_structure(text, r.url)
        except Exception as ex:  # noqa: BLE001
            structure = {"parse_error": str(ex)}

    out: dict = {
        "status": "ok",
        "mode": mode,
        "source_label": source_label,
        "url": url,
        "config_path_hint": config_path_display,
        "fetched_at_http_date": formatdate(usegmt=True),
        "http_status": r.status_code,
        "final_url": r.url,
        "content_type": r.headers.get("Content-Type"),
        "bytes_saved": len(body),
        "body_truncated": truncated,
        "body_path": body_path.name,
        "requests_made": 1,
        "constraints": {
            "max_requests": MAX_REQUESTS,
            "min_delay_s": MIN_DELAY_S,
            "max_bytes_saved": MAX_BYTES,
            "timeout_s": TIMEOUT_S,
        },
        "extracted": structure,
    }
    # Bot walls often return 200 with HTML; flag for review.
    if r.status_code == 200 and isinstance(structure, dict):
        pt = (structure.get("page") or {}).get("title") or ""
        low = (pt + text[:8000]).lower()
        if "denied" in low or "captcha" in low or "perimeter" in low or "px-captcha" in low:
            out["anomaly"] = "Possible bot challenge in response (see body file)."

    write_json(meta_path, out)
    return str(meta_path)


def collect_listings_page_sample() -> str:
    url, source_label, conf_path = _resolve_url()
    prefix = _output_prefix(source_label)
    meta_path = OUTPUT_DIR / f"{prefix}_sample.json"
    if not url:
        write_json(
            meta_path,
            {
                "status": "skipped",
                "message": "Set listings_page_url in config/local/listings_page.yaml, or LISTINGS_PAGE_URL (or legacy SCRAPE_URL).",
                "config_file_hint": str(LOCAL_CONFIG),
                "config_read": conf_path,
                "constraints": {
                    "max_requests": MAX_REQUESTS,
                    "min_delay_s": MIN_DELAY_S,
                    "max_bytes_saved": MAX_BYTES,
                    "timeout_s": TIMEOUT_S,
                },
            },
        )
        return str(meta_path)
    return run_listings_discovery(
        url=url,
        source_label=source_label,
        file_prefix=prefix,
        mode="listings_page_discovery",
        config_path_display=conf_path,
    )
