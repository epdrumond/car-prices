# Discovery phase (Python)

**FIPE** (reference table, HTTP API) and a **generic HTML listings-page** probe. Outputs live under `discovery/output/` (gitignored).

## Setup

```bash
cd /path/to/car-prices
python3 -m venv .venv
source .venv/bin/activate
pip install -r discovery/requirements.txt
```

## Run

From the **repository root**:

```bash
python -m discovery.run
python -m discovery.run --source fipe
python -m discovery.run --source listings_page
```

- **`fipe`:** ~4 small requests; writes `fipe_sample.json` (Tabela FIPE, not ad prices). The FIPE API base URL is the constant `FIPE_BASE` in `discovery/sources/fipe.py`.
- **`listings_page`:** **one** `GET` (default 5 s delay before request, ~150 KB body cap). Fetches a URL and writes structured discovery JSON + raw HTML for analysis.

`--source` is `fipe`, `listings_page`, `webmotors`, or `all` (default: `fipe` + `listings_page` only — not Webmotors).

## Webmotors (discovery only)

```bash
cp config/examples/webmotors.example.yaml config/local/webmotors.yaml
# edit: listings_page_url  — one stock/listings search page
python -m discovery.run --source webmotors
```

Or: `export WEBMOTORS_LISTINGS_URL='https://...'`.

Output:

- `output/webmotors_sample.json` and `output/webmotors_body.html` — the site may return a **bot / captcha** shell; `anomaly` is set when the body looks like a challenge.
- `output/webmotors_parsed_listings.json` — **JSON-LD** plus **model years** from the `listing_url` path, **`search_context`** from `__NEXT_DATA__`, and (when the HTML includes listing cards) **km and city/state** merged from `data-testid="…vehicle_card*…_container"` markup, keyed by `source_listing_id`. If the response has JSON-LD but no card blocks (e.g. skeletons), `mileage_km` and location can stay `null` with `field_sources.not_in_ssr`; `vehicle_card_dom` counts are in the file. If JSON-LD was **truncated**, raise `SCRAPE_MAX_BYTES_SAVED`.
- `webmotors_sample.json` is updated with `jsonld_listings.count` and path to the parsed file.

## Listings page URL (any other source)

1. Copy `config/examples/listings_page.example.yaml` to `config/local/listings_page.yaml` and set `listings_page_url` (or use env; see below).
2. Optional `source_label: mysite` → files `listings_page_mysite_sample.json` / `listings_page_mysite_body.html` so different runs do not overwrite.

**Environment (overrides YAML URL if set):**

- `LISTINGS_PAGE_URL` — or legacy `SCRAPE_URL`
- `LISTINGS_PAGE_CONFIG` — path to a custom YAML (default: `config/local/listings_page.yaml` if it exists)
- Tuning: `SCRAPE_MIN_DELAY_S` (default `5.0`), `SCRAPE_MAX_BYTES_SAVED` (default `1000000`), `SCRAPE_TIMEOUT`, `SCRAPE_USER_AGENT`, `SCRAPE_MAX_REQUESTS` (must stay `1`).

## What `listings_page` extracts (generic, no per-site code)

- Page metadata: title, description, `h1`, OpenGraph tags  
- DOM summary: tag frequency, approximate text length, count of `R$ …` substrings in visible text (hint only)  
- Embedded JSON: `application/ld+json`, `application/json` in `<script>`, `id="__NEXT_DATA__"` (key previews, not full payloads)  
- **Same-site** `a[href]` sample (up to 100)  
- First elements carrying `data-*` attributes  
- Sample `main` / `article` / `section` nodes (ids/classes/`data-*` keys)

The raw HTML is always saved to `*_body.html` for you to hand-map fields into `config/local/discovery.yaml`.

## Footprint

- **Conservative by default** (one request, delay, byte cap, no link crawling).
