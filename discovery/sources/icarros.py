"""
iCarros: requires OAuth / partner credentials. Writes a structure-only sample when not configured.
"""
from __future__ import annotations

import os

from discovery.paths import OUTPUT_DIR
from discovery.writers import write_json

OUTPUT_FILE = OUTPUT_DIR / "icarros_sample.json"

# Fields we expect to map in later phases (placeholders, not real keys from iCarros).
EXPECTED_LISTING_KEYS = [
    "source_listing_id",
    "title",
    "price_brl",
    "model_year",
    "mileage_km",
    "state",
    "city",
    "fuel",
    "transmission",
    "url",
]


def collect_icarros_sample() -> str:
    if os.environ.get("ICARROS_ACCESS_TOKEN"):
        out = {
            "source": "icarros",
            "status": "not_implemented",
            "message": "Token present; wire API calls in a later task using official docs.",
            "expected_fields": EXPECTED_LISTING_KEYS,
        }
    else:
        out = {
            "source": "icarros",
            "status": "needs_credentials",
            "message": "Set ICARROS_ACCESS_TOKEN (or local config) after registering with iCarros.",
            "expected_fields": EXPECTED_LISTING_KEYS,
            "docs": "https://www.icarros.com.br/apidocs/apiOauth.html",
            "listings": [],
        }
    write_json(OUTPUT_FILE, out)
    return str(OUTPUT_FILE)
