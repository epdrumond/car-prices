# Discovery phase (Python)

Small, **bounded** HTTP calls that write **raw JSON samples** under `output/` for schema and field analysis. This is not the production pipeline.

## Setup

```bash
cd /path/to/car-prices
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r discovery/requirements.txt
```

## Run

From the **repository root**:

```bash
python -m discovery.run
python -m discovery.run --source fipe
python -m discovery.run --source mercadolivre
```

`--source` can be `fipe`, `mercadolivre`, `icarros`, `olx`, or `all` (default).

## Outputs

| File | Behavior |
|------|----------|
| `output/fipe_sample.json` | **FIPE** reference table: excerpt of marcas + one full brand/model/year price chain (4 requests). Not listing prices. |
| `output/mercadolivre_sample.json` | **Mercado Livre** public API: category + site; search may be `forbidden` without a developer app token. |
| `output/icarros_sample.json` | **Placeholder** until `ICARROS_ACCESS_TOKEN` and API calls are implemented. |
| `output/olx_sample.json` | **Placeholder** until `OLX_ACCESS_TOKEN` and API calls are implemented. |

`discovery/output/` is **gitignored**; samples stay on your machine.

## Footprint

- **FIPE:** 4 requests per run (fixed small chain).
- **Mercado Livre:** 3 requests (category, site, one search attempt).
- **iCarros / OLX:** 0 network calls (file-only placeholders).

## Layout

- `run.py` — CLI entrypoint.
- `sources/` — one module per data source.
- `paths.py`, `writers.py`, `http_utils.py` — shared helpers.
