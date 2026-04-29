# car-prices

End-to-end project for the extraction, processing and analysis for car prices in Brazil. **Implementation is in Python 3** (ingestion, processing, database access, and analysis), with config-driven behavior and a kept-small footprint toward external data sources.

**Discovery scripts (Phase 1):** the [`discovery/`](discovery/README.md) folder fetches a **FIPE** reference sample and runs a **generic one-page** HTML listing discovery (any URL in local config). It writes under `discovery/output/` (gitignored). Run: `pip install -r discovery/requirements.txt` then `python -m discovery.run`.

**Local discovery and source config:** copy templates from `config/examples/` into `config/local/` (see [config/examples/README.md](config/examples/README.md) and [PROJECT_OUTLINE.md](PROJECT_OUTLINE.md) Phase 1) — e.g. `listings_page.yaml` for a listings URL, `discovery.yaml` for the canonical `field_map`. The `config/local/` directory is in `.gitignore` and is not pushed to the remote.
