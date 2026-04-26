"""
OLX: official integrations require tokens per OLX developers program.
Writes a structure-only sample for discovery.
"""
from __future__ import annotations

import os

from discovery.paths import OUTPUT_DIR
from discovery.writers import write_json

OUTPUT_FILE = OUTPUT_DIR / "olx_sample.json"

EXPECTED_LISTING_KEYS = [
    "source_listing_id",
    "title",
    "price_brl",
    "model_year",
    "mileage_km",
    "state",
    "city",
    "url",
    "ad_list_id",
]


def collect_olx_sample() -> str:
    if os.environ.get("OLX_ACCESS_TOKEN"):
        out = {
            "source": "olx",
            "status": "not_implemented",
            "message": "Token present; wire API calls in a later task per developers.olx.com.br.",
            "expected_fields": EXPECTED_LISTING_KEYS,
        }
    else:
        out = {
            "source": "olx",
            "status": "needs_credentials",
            "message": "Set OLX_ACCESS_TOKEN (or project config) for authenticated endpoints.",
            "expected_fields": EXPECTED_LISTING_KEYS,
            "docs": "https://developers.olx.com.br/",
            "listings": [],
        }
    write_json(OUTPUT_FILE, out)
    return str(OUTPUT_FILE)
