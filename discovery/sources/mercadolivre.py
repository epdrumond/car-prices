"""
Mercado Livre (Brasil): public read-only API for categories / site metadata.
Listing *search* often returns 403 without a registered app / token from some networks;
we still record category and search outcome for schema discovery.
"""
from __future__ import annotations

from discovery.http_utils import get_json_soft
from discovery.paths import OUTPUT_DIR
from discovery.writers import write_json

API = "https://api.mercadolibre.com"
OUTPUT_FILE = OUTPUT_DIR / "mercadolivre_sample.json"

# "Carros e Caminhonetes" under the vehicles root; child of MLB1743
CATEGORY_CARS = "MLB1744"


def collect_mercadolivre_sample() -> str:
    cat, s_cat, err = get_json_soft(f"{API}/categories/{CATEGORY_CARS}")
    site, s_site, err2 = get_json_soft(f"{API}/sites/MLB")
    search, s_search, s_err = get_json_soft(
        f"{API}/sites/MLB/search",
        params={"category": CATEGORY_CARS, "limit": 3},
    )
    if err or err2:
        raise RuntimeError(f"ML category or site request failed: {err or err2}")

    if isinstance(search, dict) and search.get("message") == "forbidden":
        search_payload = {
            "http_status": s_search,
            "error": search,
            "hint": "Search may need an app token; see https://developers.mercadolivre.com.br/",
        }
    else:
        search_payload = {
            "http_status": s_search,
            "body": search,
        }

    out = {
        "source": "mercado_livre_api",
        "api_base": API,
        "category_id_cars": CATEGORY_CARS,
        "note": "Category + site are public; item search is often token/IP restricted for bots.",
        "category": cat,
        "site_mlb": site,
        "search_listings_sample": search_payload,
    }
    write_json(OUTPUT_FILE, out)
    return str(OUTPUT_FILE)
