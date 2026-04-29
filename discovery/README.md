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

`--source` is `fipe`, `listings_page`, or `all` (default: both).

## Listings page URL (any source)

1. Copy `config/examples/listings_page.example.yaml` to `config/local/listings_page.yaml` and set `listings_page_url` (or use env; see below).
2. Optional `source_label: mysite` → files `listings_page_mysite_sample.json` / `listings_page_mysite_body.html` so different runs do not overwrite.

**Environment (overrides YAML URL if set):**

- `LISTINGS_PAGE_URL` — or legacy `SCRAPE_URL`
- `LISTINGS_PAGE_CONFIG` — path to a custom YAML (default: `config/local/listings_page.yaml` if it exists)
- Tuning: `SCRAPE_MIN_DELAY_S` (default `5.0`), `SCRAPE_MAX_BYTES_SAVED` (default `150000`), `SCRAPE_TIMEOUT`, `SCRAPE_USER_AGENT`, `SCRAPE_MAX_REQUESTS` (must stay `1`).

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
