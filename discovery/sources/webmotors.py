"""
Webmotors — discovery-only, single GET of a *listings* (estoque) page.

URL from ``WEBMOTORS_LISTINGS_URL`` or ``config/local/webmotors.yaml`` (gitignored).
Same conservative limits as the generic listings fetch; see :func:`run_listings_discovery`.

Respect the site terms and robots policy; automated clients may see a bot interstitial
(check ``anomaly`` in the JSON and the ``_body`` file).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

from discovery.paths import OUTPUT_DIR, write_json
from discovery.sources.listings_page import run_listings_discovery
from discovery.webmotors_jsonld import extract_webmotors_page_bundle

_DISCOVERY_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_LOCAL = _DISCOVERY_ROOT.parent / "config" / "local" / "webmotors.yaml"


def _load_yaml(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _resolve() -> tuple[str, str]:
    u = (os.environ.get("WEBMOTORS_LISTINGS_URL") or "").strip()
    p = (os.environ.get("WEBMOTORS_CONFIG") or "").strip()
    path = Path(p) if p else _DEFAULT_LOCAL
    cfg = _load_yaml(path)
    if not u and isinstance(cfg, dict):
        raw = cfg.get("listings_page_url") or cfg.get("url")
        u = str(raw).strip() if raw else ""
    return u, str(path)


def collect_webmotors_sample() -> str:
    url, path_str = _resolve()
    if not url:
        out = OUTPUT_DIR / "webmotors_sample.json"
        write_json(
            out,
            {
                "status": "skipped",
                "source": "webmotors",
                "message": "Set listings_page_url in config/local/webmotors.yaml (see config/examples) or WEBMOTORS_LISTINGS_URL.",
                "config_path": path_str,
            },
        )
        return str(out)
    sample_path = run_listings_discovery(
        url=url,
        source_label="webmotors",
        file_prefix="webmotors",
        mode="webmotors_listings_discovery",
        config_path_display=path_str,
    )
    # JSON-LD + URL years + __NEXT_DATA__ search context (see webmotors_jsonld).
    body_path = OUTPUT_DIR / "webmotors_body.html"
    rows: list = []
    if body_path.is_file():
        body = body_path.read_text(encoding="utf-8", errors="replace")
        bundle = extract_webmotors_page_bundle(body)
        rows = bundle.get("listings") or []
        out = {"source": "webmotors", **bundle}
        write_json(OUTPUT_DIR / "webmotors_parsed_listings.json", out)

    try:
        with open(sample_path, encoding="utf-8") as f:
            sample = json.load(f)
    except (OSError, json.JSONDecodeError):
        return sample_path
    if isinstance(sample, dict) and sample.get("status") == "ok":
        sample["jsonld_listings"] = {
            "count": len(rows),
            "artifact": "webmotors_parsed_listings.json",
            "note": (
                "JSON-LD + model year from URL + search_context. "
                "Mileage and location are merged from vehicle card DOM (data-testid) when the HTML includes "
                "those cards; some responses only include JSON-LD, so field_sources may be not_in_ssr. "
                "See webmotors_parsed_listings.json: vehicle_card_dom, ssr_data_note."
            ),
        }
        write_json(Path(sample_path), sample)
    return sample_path
